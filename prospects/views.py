from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
import csv
import io
from datetime import datetime
from urllib.parse import urlencode
from .models import Prospect, UploadHistory
from django.core.paginator import Paginator


def count_filled_fields(prospect_dict):
    """Compte le nombre de champs remplis dans un dictionnaire de prospect"""
    return sum(1 for v in prospect_dict.values() if v and str(v).strip())


@login_required
@ensure_csrf_cookie
def prospect_list(request):
    """Affiche la liste des prospects avec recherche/filtre/pagination"""
    qs = Prospect.objects.all()

    # Filtres
    q = (request.GET.get('q') or '').strip()
    converted = (request.GET.get('converted') or '').strip()  # '', 'yes', 'no'
    source = (request.GET.get('source') or '').strip()
    activity_type = (request.GET.get('activity_type') or '').strip()
    level = (request.GET.get('level') or '').strip()
    start = (request.GET.get('start') or '').strip()
    end = (request.GET.get('end') or '').strip()

    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )

    if converted == 'yes':
        qs = qs.filter(converted=True)
    elif converted == 'no':
        qs = qs.filter(converted=False)

    if source:
        qs = qs.filter(source__iexact=source)

    if activity_type:
        qs = qs.filter(activity_type__icontains=activity_type)

    if level:
        qs = qs.filter(level__iexact=level)

    # Filtre par dates
    from datetime import datetime as _dt
    def _parse_date(val):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                return _dt.strptime(val, fmt)
            except Exception:
                continue
        return None

    if start:
        d = _parse_date(start)
        if d:
            qs = qs.filter(created_at__gte=d)

    if end:
        d = _parse_date(end)
        if d:
            qs = qs.filter(created_at__lte=d)

    total = qs.count()
    converted_count = qs.filter(converted=True).count()
    not_converted_count = qs.filter(converted=False).count()

    # Tri
    sort = (request.GET.get('sort') or 'created_at').strip()
    direction = (request.GET.get('dir') or 'desc').strip().lower()
    if direction not in ('asc', 'desc'):
        direction = 'desc'

    allowed_sorts = {
        'name': ('last_name', 'first_name'),
        'contact': ('email', 'phone'),
        'level': ('level',),
        'activity': ('activity_type',),
        'source': ('source',),
        'status': ('converted',),
        'created_at': ('created_at',),
    }

    if sort not in allowed_sorts:
        sort = 'created_at'
        direction = 'desc'

    order_fields = []
    for field in allowed_sorts[sort]:
        order_fields.append(field if direction == 'asc' else f'-{field}')

    qs = qs.order_by(*order_fields)

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 25))
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    # Construire la query string pour réutiliser les filtres dans les liens (sauf page)
    base_query_params = {
        'q': q,
        'converted': converted,
        'source': source,
        'activity_type': activity_type,
        'level': level,
        'start': start,
        'end': end,
        'per_page': per_page,
    }
    base_query = urlencode({k: v for k, v in base_query_params.items() if v not in [None, '']})

    # Sources / levels / activities distincts (pour dropdowns)
    distinct_sources = list(Prospect.objects.exclude(source='').exclude(source__isnull=True).values_list('source', flat=True).distinct().order_by('source'))
    distinct_levels = list(Prospect.objects.exclude(level='').exclude(level__isnull=True).values_list('level', flat=True).distinct().order_by('level'))
    distinct_activities = list(Prospect.objects.exclude(activity_type='').exclude(activity_type__isnull=True).values_list('activity_type', flat=True).distinct().order_by('activity_type'))

    context = {
        'prospects': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'total': total,
        'converted': converted_count,
        'not_converted': not_converted_count,
        # Filtres (pour conserver les valeurs)
        'q': q,
        'f_converted': converted,
        'f_source': source,
        'f_activity_type': activity_type,
        'f_level': level,
        'f_start': start,
        'f_end': end,
        'distinct_sources': distinct_sources,
        'distinct_levels': distinct_levels,
        'distinct_activities': distinct_activities,
        'per_page': per_page,
        'sort': sort,
        'direction': direction,
        'base_query': base_query,
    }
    
    # Si requête HTMX, renvoyer uniquement le template partiel
    if request.headers.get('HX-Request'):
        return render(request, 'prospects/_search_results_partial.html', context)
    
    # Sinon, renvoyer la page complète
    return render(request, 'prospects/prospect_list.html', context)


@login_required
@require_http_methods(["POST"])
def upload_csv(request):
    """Upload et parse un fichier CSV"""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'Aucun fichier'}, status=400)
    
    csv_file = request.FILES['file']
    
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'success': False, 'error': 'Le fichier doit être un CSV'}, status=400)
    
    try:
        # Lire tout le contenu (gestion du BOM éventuel) et parser
        content = csv_file.read().decode('utf-8-sig')
        stream = io.StringIO(content)
        csv_reader = csv.DictReader(stream)

        created = 0
        updated = 0
        processed = 0
        errors = []
        created_details = []  # Détails des prospects créés
        updated_details = []  # Détails des prospects fusionnés
        duplicates = []  # Liste pour tracker les doublons

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                processed += 1
                # Parser la date de naissance éventuelle (AAAA-MM-JJ ou JJ/MM/AAAA)
                birth_date = None
                raw_bd = row.get('Date de naissance') or row.get('Date de naissance '.strip())
                if raw_bd:
                    raw_bd = raw_bd.strip()
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'):
                        try:
                            birth_date = datetime.strptime(raw_bd, fmt).date()
                            break
                        except Exception:
                            continue

                # Parser l'âge
                age_val = None
                raw_age = row.get('Âge') or row.get('Age') or row.get('age')
                if raw_age:
                    try:
                        age_val = int(str(raw_age).strip())
                    except Exception:
                        age_val = None

                # Récupérer les infos critiques pour détecter les doublons
                email = (row.get('Email') or '').strip()
                first_name = (row.get('Prénom') or row.get('Prenom') or '').strip()
                last_name = (row.get('Nom') or '').strip()
                phone = (row.get('Téléphone') or row.get('Telephone') or row.get('Tel') or '').strip()
                specific_course = (row.get('Cours spécifique') or row.get('Cours specifique') or '').strip()
                
                if not email:
                    raise ValueError("Email manquant")

                new_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'age': age_val,
                    'birth_date': birth_date,
                    'level': (row.get('Niveau') or '').strip(),
                    'source': (row.get('Source') or '').strip(),
                    'activity_type': (row.get("Type d'activité") or row.get('Type activite') or '').strip(),
                    'specific_course': specific_course,
                    'message': (row.get('Message') or '').strip(),
                    'notes': (row.get('Notes') or '').strip(),
                }

                # Détection de doublons : Nom + Prénom + Email + Cours + Date de naissance
                duplicate_query = Prospect.objects.filter(
                    first_name__iexact=first_name,
                    last_name__iexact=last_name,
                    email__iexact=email
                )
                
                # Ajouter le filtre sur le cours s'il est fourni
                if specific_course:
                    duplicate_query = duplicate_query.filter(specific_course__iexact=specific_course)
                
                # Ajouter le filtre sur la date de naissance s'elle est fournie
                if birth_date:
                    duplicate_query = duplicate_query.filter(birth_date=birth_date)
                
                prospect = duplicate_query.first()
                
                if prospect:
                    # Prospect trouvé → fusionner les données en gardant les plus complètes
                    old_data = {
                        'first_name': prospect.first_name,
                        'last_name': prospect.last_name,
                        'email': prospect.email,
                        'phone': prospect.phone,
                        'age': prospect.age,
                        'birth_date': prospect.birth_date,
                        'level': prospect.level,
                        'source': prospect.source,
                        'activity_type': prospect.activity_type,
                        'specific_course': prospect.specific_course,
                        'message': prospect.message,
                        'notes': prospect.notes,
                    }
                    
                    # Déterminer les raisons du doublon
                    reasons = []
                    if first_name.lower() == prospect.first_name.lower():
                        reasons.append(f"Prénom: {first_name}")
                    if last_name.lower() == prospect.last_name.lower():
                        reasons.append(f"Nom: {last_name}")
                    if email.lower() == prospect.email.lower():
                        reasons.append(f"Email: {email}")
                    if specific_course and specific_course.lower() == prospect.specific_course.lower():
                        reasons.append(f"Cours: {specific_course}")
                    if birth_date and birth_date == prospect.birth_date:
                        reasons.append(f"Naissance: {birth_date}")
                    
                    # Enregistrer le doublon trouvé
                    duplicates.append({
                        'row': row_num,
                        'new': {
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'phone': phone,
                            'birth_date': str(birth_date) if birth_date else '',
                            'specific_course': specific_course,
                        },
                        'existing': {
                            'id': prospect.id,
                            'first_name': prospect.first_name,
                            'last_name': prospect.last_name,
                            'email': prospect.email,
                            'phone': prospect.phone,
                            'birth_date': str(prospect.birth_date) if prospect.birth_date else '',
                            'specific_course': prospect.specific_course,
                        },
                        'reasons': reasons,
                    })
                    
                    # Compter les champs remplis dans chaque version
                    old_count = count_filled_fields(old_data)
                    new_count = count_filled_fields(new_data)
                    
                    # Fusionner : prendre la version la plus complète pour chaque champ
                    # IMPORTANT: Ne jamais écraser les champs sensibles (converted, notes)
                    merged_data = {}
                    for key in new_data.keys():
                        old_val = old_data.get(key)
                        new_val = new_data.get(key)
                        
                        # Garder la valeur non-vide, sinon la valeur nouvelle
                        if old_val and str(old_val).strip():
                            merged_data[key] = old_val
                        elif new_val and str(new_val).strip():
                            merged_data[key] = new_val
                        else:
                            merged_data[key] = new_val or old_val
                    
                    # Appliquer les données fusionnées
                    # IMPORTANT: Ne jamais modifier converted (statut de conversion)
                    for key, value in merged_data.items():
                        if key != 'converted':  # Protéger le statut
                            setattr(prospect, key, value)
                    
                    # Conserver le statut de conversion existant
                    # prospect.converted reste inchangé
                    prospect.save()
                    
                    # Enregistrer les détails de la fusion
                    updated_details.append({
                        'row': row_num,
                        'prospect_id': prospect.id,
                        'name': f"{prospect.first_name} {prospect.last_name}",
                        'email': prospect.email,
                        'reason': 'Doublon détecté - Données fusionnées',
                        'criteria': reasons,
                    })
                    updated += 1
                else:
                    # Nouveau prospect → création
                    prospect = Prospect.objects.create(**new_data)
                    
                    # Enregistrer les détails de la création
                    created_details.append({
                        'row': row_num,
                        'prospect_id': prospect.id,
                        'name': f"{prospect.first_name} {prospect.last_name}",
                        'email': prospect.email,
                        'reason': 'Nouveau prospect créé',
                    })
                    created += 1
            except Exception as e:
                errors.append(f"Ligne {row_num}: {str(e)}")

        message = f"Import terminé. {created} nouveau(x) prospect(s) ajouté(s), {updated} doublons fusionnés."
        if errors:
            message += f" {len(errors)} erreur(s)."

        # Sauvegarder dans l'historique
        upload_record = UploadHistory.objects.create(
            filename=csv_file.name,
            total_processed=processed,
            created_count=created,
            updated_count=updated,
            created_data=created_details,
            updated_data=updated_details,
            duplicates_data=duplicates,
            errors_data=errors
        )

        return JsonResponse({
            'success': True,
            'message': message,
            'created': created,
            'skipped': updated,
            'processed': processed,
            'errors': errors,
            'duplicates': duplicates,
            'upload_id': upload_record.id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def get_prospect_data(request, prospect_id):
    """Retourne les données d'un prospect en JSON pour pré-remplissage"""
    prospect = get_object_or_404(Prospect, pk=prospect_id)
    
    return JsonResponse({
        'first_name': prospect.first_name,
        'last_name': prospect.last_name,
        'email': prospect.email,
        'phone': prospect.phone,
        'age': prospect.age or '',
        'birth_date': prospect.birth_date.isoformat() if prospect.birth_date else '',
        'message': prospect.message,
        'activity_summary': prospect.get_activity_summary(),
    })


@login_required
@require_http_methods(["POST"])
def cancel_conversion(request, prospect_id):
    """Annule la conversion d'un prospect : remet converted=False et supprime l'étudiant correspondant"""
    prospect = get_object_or_404(Prospect, pk=prospect_id)
    
    if not prospect.converted:
        return JsonResponse({'success': False, 'message': 'Ce prospect n\'est pas converti.'}, status=400)
    
    # Chercher l'étudiant avec le même email
    from students.models import Student
    deleted_count = 0
    if prospect.email:
        students = Student.objects.filter(email=prospect.email)
        deleted_count = students.count()
        students.delete()  # Le signal reset_prospect_on_student_delete va mettre converted=False automatiquement
    
    # Si pas d'email ou pas d'étudiant trouvé, on remet quand même converted=False
    if deleted_count == 0:
        prospect.converted = False
        prospect.save()
    
    message = f'Conversion annulée. {deleted_count} étudiant(s) supprimé(s).' if deleted_count > 0 else 'Conversion annulée.'
    return JsonResponse({'success': True, 'message': message})


@login_required
@require_http_methods(["GET", "POST"])
def add_prospect(request):
    """Ajouter un nouveau prospect"""
    if request.method == "POST":
        try:
            # Parser date de naissance
            birth_date = None
            bd_str = request.POST.get('birth_date', '').strip()
            if bd_str:
                from datetime import datetime
                birth_date = datetime.strptime(bd_str, '%Y-%m-%d').date()
            
            Prospect.objects.create(
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                email=request.POST.get('email', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                birth_date=birth_date,
                age=int(request.POST.get('age', 0) or 0),
                level=request.POST.get('level', '').strip(),
                source=request.POST.get('source', '').strip(),
                activity_type=request.POST.get('activity_type', '').strip(),
                specific_course=request.POST.get('specific_course', '').strip(),
                message=request.POST.get('message', '').strip(),
                notes=request.POST.get('notes', '').strip(),
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # GET: retourner le formulaire HTML
    return render(request, 'prospects/prospect_form.html', {'prospect': None})


@login_required
@require_http_methods(["GET", "POST"])
def edit_prospect(request, prospect_id):
    """Modifier un prospect existant"""
    prospect = get_object_or_404(Prospect, pk=prospect_id)
    
    if request.method == "POST":
        try:
            # Parser date de naissance
            birth_date = None
            bd_str = request.POST.get('birth_date', '').strip()
            if bd_str:
                from datetime import datetime
                birth_date = datetime.strptime(bd_str, '%Y-%m-%d').date()
            
            prospect.first_name = request.POST.get('first_name', '').strip()
            prospect.last_name = request.POST.get('last_name', '').strip()
            prospect.email = request.POST.get('email', '').strip()
            prospect.phone = request.POST.get('phone', '').strip()
            prospect.birth_date = birth_date
            prospect.age = int(request.POST.get('age', 0) or 0)
            prospect.level = request.POST.get('level', '').strip()
            prospect.source = request.POST.get('source', '').strip()
            prospect.activity_type = request.POST.get('activity_type', '').strip()
            prospect.specific_course = request.POST.get('specific_course', '').strip()
            prospect.message = request.POST.get('message', '').strip()
            prospect.notes = request.POST.get('notes', '').strip()
            prospect.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    # GET: retourner le formulaire HTML pré-rempli
    return render(request, 'prospects/prospect_form.html', {'prospect': prospect})


@login_required
@require_http_methods(["POST"])
def delete_prospect(request, prospect_id):
    """Supprimer un prospect"""
    prospect = get_object_or_404(Prospect, pk=prospect_id)
    prospect.delete()
    return JsonResponse({'success': True})


@login_required
def prospect_dashboard(request):
    """Dashboard des prospects avec statistiques et graphiques"""
    import json
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    today = timezone.now().date()
    
    # Données globales
    total_prospects = Prospect.objects.count()
    converted_count = Prospect.objects.filter(converted=True).count()
    unconverted_count = total_prospects - converted_count
    conversion_rate = (converted_count / total_prospects * 100) if total_prospects > 0 else 0
    
    # Conversions par période
    last_month_start = today.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    converted_last_month = Prospect.objects.filter(
        converted=True,
        updated_at__date__gte=last_month_start,
        updated_at__date__lte=today
    ).count()
    
    # Conversions par trimestre (année académique 9-8)
    month = today.month
    if month in [9, 10, 11]:
        quarter = 'Q1'
        q_start = today.replace(month=9, day=1)
    elif month in [12, 1, 2]:
        quarter = 'Q2'
        if month in [12]:
            q_start = today.replace(month=12, day=1)
        else:
            q_start = today.replace(year=today.year-1, month=12, day=1)
    elif month in [3, 4, 5]:
        quarter = 'Q3'
        q_start = today.replace(month=3, day=1)
    else:
        quarter = 'Q4'
        q_start = today.replace(month=6, day=1)
    
    converted_last_quarter = Prospect.objects.filter(
        converted=True,
        updated_at__date__gte=q_start
    ).count()
    
    # Sujets/Cours les plus demandés
    top_courses = Prospect.objects.exclude(
        specific_course=''
    ).values('specific_course').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    courses_data = {item['specific_course']: item['count'] for item in top_courses}
    
    # Activités/Types les plus demandées
    top_activities = Prospect.objects.exclude(
        activity_type=''
    ).values('activity_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    activities_data = {item['activity_type']: item['count'] for item in top_activities}
    
    # Niveaux demandés
    level_dist = Prospect.objects.exclude(
        level=''
    ).values('level').annotate(
        count=Count('id')
    ).order_by('-count')
    
    levels_data = {item['level']: item['count'] for item in level_dist}
    
    # Sources
    source_dist = Prospect.objects.exclude(
        source=''
    ).values('source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    sources_data = {item['source']: item['count'] for item in source_dist}
    
    # Modalité estimée (En ligne vs Présentiel) - basée sur le titre du cours
    all_prospects = Prospect.objects.all()
    online_count = 0
    in_person_count = 0
    
    for prospect in all_prospects:
        course_title = (prospect.specific_course or '').lower()
        if 'en ligne' in course_title or 'online' in course_title:
            online_count += 1
        else:
            in_person_count += 1
    
    # Conversions timeline (par mois) - 12 derniers mois
    from datetime import date
    conversions_by_month = {}
    
    # Générer les 12 derniers mois
    current_date = date.today()
    for i in range(11, -1, -1):
        # Calculer le mois
        target_month = current_date.month - i
        target_year = current_date.year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # Début et fin du mois
        from calendar import monthrange
        month_start = date(target_year, target_month, 1)
        last_day = monthrange(target_year, target_month)[1]
        month_end = date(target_year, target_month, last_day)
        
        # Compter les conversions
        count = Prospect.objects.filter(
            converted=True,
            updated_at__date__gte=month_start,
            updated_at__date__lte=month_end
        ).count()
        
        month_label = month_start.strftime('%b %Y')
        conversions_by_month[month_label] = count
    
    context = {
        'total_prospects': total_prospects,
        'converted_count': converted_count,
        'unconverted_count': unconverted_count,
        'conversion_rate': round(conversion_rate, 1),
        'converted_last_month': converted_last_month,
        'converted_last_quarter': converted_last_quarter,
        'current_quarter': quarter,
        'courses_data': courses_data,
        'activities_data': activities_data,
        'levels_data': levels_data,
        'sources_data': sources_data,
        'conversions_by_month': conversions_by_month,
        'online_count': online_count,
        'in_person_count': in_person_count,
        'today': today,
    }
    
    return render(request, 'prospects/prospect_dashboard.html', context)

@login_required
def upload_history(request):
    """Affiche l'historique des uploads"""
    uploads = UploadHistory.objects.all()
    paginator = Paginator(uploads, 20)
    page = int(request.GET.get('page', 1))
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'uploads': page_obj,
    }
    return render(request, 'prospects/upload_history.html', context)


@login_required
def upload_detail(request, upload_id):
    """Affiche les détails d'un upload"""
    upload = get_object_or_404(UploadHistory, pk=upload_id)
    
    context = {
        'upload': upload,
    }
    return render(request, 'prospects/upload_detail.html', context)