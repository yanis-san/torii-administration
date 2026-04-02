# core/views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum, Q
from academics.models import CourseSession, Cohort, Subject
from students.models import Enrollment, StudentAnnualFee
from finance.models import Payment
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from .models import User, AcademicYear
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
import threading
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from .schedule_generator import generate_schedule_pdf

@login_required
def dashboard(request):
    today = timezone.now().date()
    user = request.user

    # Vérifier si l'utilisateur est un professeur
    is_teacher = user.is_authenticated and user.is_teacher

    if is_teacher:
        # DASHBOARD PROFESSEUR : Voir TOUTES ses séances (titulaire OU remplaçant)
        todays_sessions = CourseSession.objects.filter(
            teacher=user,  # Toutes les séances où il est le prof (titulaire ou remplaçant)
            date=today
        ).select_related('cohort', 'classroom', 'teacher').order_by('start_time')

        # Séance mise en avant sur l'accueil prof
        now_time = timezone.localtime().time()
        featured_session = None
        current_session = None
        next_today_session = None
        featured_timing = ''
        featured_in_minutes = None

        for session in todays_sessions:
            if session.start_time <= now_time <= session.end_time:
                current_session = session
                break

        if current_session:
            featured_session = current_session
            featured_timing = 'LIVE'
        else:
            for session in todays_sessions:
                if session.start_time >= now_time:
                    next_today_session = session
                    break
            featured_session = next_today_session or (todays_sessions[0] if todays_sessions else None)
            if next_today_session:
                featured_timing = 'UPCOMING'

        if featured_session and featured_timing == 'UPCOMING':
            delta_minutes = int(
                (
                    datetime.combine(today, featured_session.start_time)
                    - datetime.combine(today, now_time)
                ).total_seconds() // 60
            )
            if delta_minutes >= 0:
                featured_in_minutes = delta_minutes

        anchor_time = featured_session.start_time if featured_session else now_time

        previous_session = CourseSession.objects.filter(
            teacher=user
        ).filter(
            Q(date__lt=today) | Q(date=today, start_time__lt=anchor_time)
        ).select_related('cohort').order_by('-date', '-start_time').first()

        next_session = CourseSession.objects.filter(
            teacher=user
        ).filter(
            Q(date__gt=today) | Q(date=today, start_time__gt=anchor_time)
        ).select_related('cohort').order_by('date', 'start_time').first()

        other_today_sessions = [
            s for s in todays_sessions if not featured_session or s.id != featured_session.id
        ]

        # Ses groupes actifs : cohorts où il est titulaire OU où il a au moins une séance
        cohorts_as_teacher = Cohort.objects.filter(teacher=user)
        cohort_ids_with_sessions = CourseSession.objects.filter(
            teacher=user
        ).values_list('cohort_id', flat=True).distinct()
        my_cohorts = Cohort.objects.filter(
            id__in=list(cohorts_as_teacher.values_list('id', flat=True)) + list(cohort_ids_with_sessions)
        ).prefetch_related('enrollments__student').order_by('name').distinct()

        # Statistiques personnelles
        my_total_students = Enrollment.objects.filter(
            cohort__teacher=user,
            is_active=True
        ).count()

        # Nombre de séances complétées ce mois
        completed_this_month = CourseSession.objects.filter(
            teacher=user,
            status='COMPLETED',
            date__month=today.month,
            date__year=today.year
        ).count()

        context = {
            'is_teacher': True,
            'sessions': todays_sessions,
            'featured_session': featured_session,
            'featured_timing': featured_timing,
            'featured_in_minutes': featured_in_minutes,
            'previous_session': previous_session,
            'next_session': next_session,
            'other_today_sessions': other_today_sessions,
            'my_cohorts': my_cohorts,
            'total_students': my_total_students,
            'completed_this_month': completed_this_month,
            'today': today,
        }
    else:
        # DASHBOARD ADMIN : Voir TOUT
        todays_sessions = CourseSession.objects.filter(
            date=today
        ).select_related('cohort', 'teacher', 'classroom').order_by('start_time')

        # Chiffres globaux
        total_students = Enrollment.objects.filter(is_active=True).count()

        # Année académique courante
        current_year = AcademicYear.get_current()

        # Filtres depuis la requête GET
        filter_year = request.GET.get('year')  # ID de l'année académique
        filter_period = request.GET.get('period', 'academic_year')  # 'month', 'quarter', 'academic_year'
        filter_language = request.GET.get('language')  # ID du Subject (langue)
        filter_modality = request.GET.get('modality')  # 'ONLINE', 'IN_PERSON'
        filter_type = request.GET.get('type')  # 'individual', 'group'

        # Par défaut, utiliser l'année académique courante
        if not filter_year and current_year:
            filter_year = str(current_year.id)

        # Récupérer l'année sélectionnée
        selected_year = None
        if filter_year:
            try:
                selected_year = AcademicYear.objects.get(id=int(filter_year))
            except:
                selected_year = current_year

        # Calcul des revenus selon le filtre

        # Revenus par année académique
        academic_year_income = 0
        monthly_income = 0
        quarterly_data = {}
        languages_income = {}  # {language_name: income}
        modality_income = {}   # {'Présentiel': X, 'En ligne': Y}
        type_income = {}       # {'Groupe': X, 'Individuel': Y}

        if selected_year:
            # Déterminer la clause de filtre pour la langue
            language_filter = Q()
            if filter_language:
                try:
                    language_obj = Subject.objects.get(id=int(filter_language))
                    language_filter = Q(enrollment__cohort__subject=language_obj)
                except:
                    pass

            # Déterminer la clause de filtre pour la modalité
            modality_filter = Q()
            if filter_modality:
                modality_filter = Q(enrollment__cohort__modality=filter_modality)

            # Déterminer la clause de filtre pour le type
            type_filter = Q()
            if filter_type == 'individual':
                type_filter = Q(enrollment__cohort__is_individual=True)
            elif filter_type == 'group':
                type_filter = Q(enrollment__cohort__is_individual=False)

            # Combiner tous les filtres
            combined_filter = language_filter & modality_filter & type_filter

            # Revenus de toute l'année académique
            academic_year_income = Payment.objects.filter(
                date__gte=selected_year.start_date,
                date__lte=selected_year.end_date
            ).filter(combined_filter).aggregate(Sum('amount'))['amount__sum'] or 0

            # Revenus par langue
            all_languages = Subject.objects.all().order_by('name')
            for lang in all_languages:
                lang_income = Payment.objects.filter(
                    date__gte=selected_year.start_date,
                    date__lte=selected_year.end_date,
                    enrollment__cohort__subject=lang
                ).filter(modality_filter & type_filter).aggregate(Sum('amount'))['amount__sum'] or 0
                if lang_income > 0:
                    languages_income[lang.name] = float(lang_income)

            # Revenus par modalité
            for modality_key, modality_label in [('IN_PERSON', 'Présentiel'), ('ONLINE', 'En ligne')]:
                modality_rev = Payment.objects.filter(
                    date__gte=selected_year.start_date,
                    date__lte=selected_year.end_date,
                    enrollment__cohort__modality=modality_key
                ).filter(language_filter & type_filter).aggregate(Sum('amount'))['amount__sum'] or 0
                if modality_rev > 0:
                    modality_income[modality_label] = float(modality_rev)

            # Revenus par type
            for is_ind, type_label in [(True, 'Individuel'), (False, 'Groupe')]:
                type_rev = Payment.objects.filter(
                    date__gte=selected_year.start_date,
                    date__lte=selected_year.end_date,
                    enrollment__cohort__is_individual=is_ind
                ).filter(language_filter & modality_filter).aggregate(Sum('amount'))['amount__sum'] or 0
                if type_rev > 0:
                    type_income[type_label] = float(type_rev)

            # Revenus par mois de l'année académique
            monthly_breakdown = []
            current_date = selected_year.start_date
            while current_date <= selected_year.end_date:
                month_end = current_date.replace(day=1) + timedelta(days=32)
                month_end = month_end.replace(day=1) - timedelta(days=1)
                if month_end > selected_year.end_date:
                    month_end = selected_year.end_date

                month_income = Payment.objects.filter(
                    date__gte=current_date,
                    date__lte=month_end
                ).filter(language_filter).aggregate(Sum('amount'))['amount__sum'] or 0

                month_name = current_date.strftime('%B %Y')
                monthly_breakdown.append({
                    'name': month_name,
                    'value': float(month_income),
                    'date': current_date.strftime('%Y-%m')
                })

                current_date = month_end + timedelta(days=1)

            # Revenus par trimestre
            quarterly_data = {
                'Q1': 0,  # Sept-Nov
                'Q2': 0,  # Déc-Fév
                'Q3': 0,  # Mar-Mai
                'Q4': 0,  # Juin-Août
            }

            for payment in Payment.objects.filter(
                date__gte=selected_year.start_date,
                date__lte=selected_year.end_date
            ).filter(language_filter):
                month = payment.date.month
                # Déterminer le trimestre (année académique 9-8)
                if month in [9, 10, 11]:
                    quarterly_data['Q1'] += float(payment.amount)
                elif month in [12, 1, 2]:
                    quarterly_data['Q2'] += float(payment.amount)
                elif month in [3, 4, 5]:
                    quarterly_data['Q3'] += float(payment.amount)
                else:  # 6, 7, 8
                    quarterly_data['Q4'] += float(payment.amount)

            # Revenu du mois actuel (pour info)
            monthly_income = Payment.objects.filter(
                date__month=today.month,
                date__year=today.year
            ).filter(language_filter).aggregate(Sum('amount'))['amount__sum'] or 0
        else:
            monthly_breakdown = []

        # Calcul des frais d'inscription pour l'année sélectionnée
        registration_fees_total = 0
        paid_registrations_count = 0
        if selected_year:
            paid_registrations = StudentAnnualFee.objects.filter(
                academic_year=selected_year,
                is_paid=True
            )
            paid_registrations_count = paid_registrations.count()
            registration_fees_total = paid_registrations_count * selected_year.registration_fee_amount

        # Liste de toutes les années académiques pour le filtre
        all_academic_years = AcademicYear.objects.all().order_by('-start_date')
        
        # Liste de toutes les langues (subjects)
        all_languages = Subject.objects.all().order_by('name')

        context = {
            'is_teacher': False,
            'sessions': todays_sessions,
            'total_students': total_students,
            'monthly_income': monthly_income,
            'academic_year_income': academic_year_income,
            'registration_fees_total': registration_fees_total,
            'paid_registrations_count': paid_registrations_count,
            'current_academic_year': current_year,
            'selected_year': selected_year,
            'all_academic_years': all_academic_years,
            'all_languages': all_languages,
            'filter_language': filter_language,
            'filter_modality': filter_modality,
            'filter_type': filter_type,
            'languages_income': languages_income,
            'modality_income': modality_income,
            'type_income': type_income,
            'filter_period': filter_period,
            'monthly_breakdown': monthly_breakdown,
            'quarterly_data': quarterly_data,
            'today': today,
        }

    return render(request, 'core/dashboard.html', context)


def login_view(request):
    """Vue de connexion"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Bienvenue {user.get_full_name() or user.username} !')

            # Rediriger vers la page demandée ou le dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Identifiant ou mot de passe incorrect.')

    return render(request, 'core/login.html')


def signup_view(request):
    """Vue d'inscription"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        is_teacher = request.POST.get('is_teacher') == 'on'

        # Validation
        if password != password_confirm:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur existe déjà.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
        else:
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_teacher=is_teacher
            )

            messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
            return redirect('login')

    return render(request, 'core/signup.html')


def logout_view(request):
    """Vue de déconnexion"""
    auth_logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


@login_required
def academic_year_list(request):
    """Liste les années scolaires avec possibilité d'ajouter/modifier/activer"""
    from .models import AcademicYear
    from django.http import JsonResponse
    
    years = AcademicYear.objects.all().order_by('-label')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            label = request.POST.get('label', '').strip()
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            is_current = request.POST.get('is_current') == 'on'
            
            if not label or not start_date or not end_date:
                return JsonResponse({'success': False, 'error': 'Tous les champs sont obligatoires'}, status=400)
            
            try:
                AcademicYear.objects.create(
                    label=label,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current
                )
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        elif action == 'edit':
            year_id = request.POST.get('year_id')
            label = request.POST.get('label', '').strip()
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if not label or not start_date or not end_date:
                return JsonResponse({'success': False, 'error': 'Tous les champs sont obligatoires'}, status=400)
            
            try:
                year = AcademicYear.objects.get(pk=year_id)
                year.label = label
                year.start_date = start_date
                year.end_date = end_date
                year.save()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        elif action == 'set_current':
            year_id = request.POST.get('year_id')
            try:
                year = AcademicYear.objects.get(pk=year_id)
                year.is_current = True
                year.save()  # save() déclenche la logique pour désactiver les autres
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        elif action == 'delete':
            year_id = request.POST.get('year_id')
            try:
                year = AcademicYear.objects.get(pk=year_id)
                year.delete()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    context = {'years': years}
    return render(request, 'core/academic_year_list.html', context)


@login_required
def backups_and_recovery(request):
    """Page pour gérer les sauvegardes et restaurations."""
    from django.core.management import call_command
    from io import StringIO
    from pathlib import Path
    from datetime import datetime
    
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Accès réservé aux administrateurs")
        return redirect('dashboard')
    
    backups_dir = Path('backups_local')
    recent_backups = []
    
    if backups_dir.exists():
        # Lister les fichiers de sauvegarde (.zip et .tar.gz)
        for backup_file in sorted(backups_dir.glob('*'), reverse=True)[:10]:
            if backup_file.is_file() and (backup_file.suffix in ['.zip', '.gz'] or backup_file.name.endswith('.tar.gz')):
                recent_backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': backup_file.stat().st_size / (1024 * 1024),
                    'date': datetime.fromtimestamp(backup_file.stat().st_mtime)
                })
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'backup':
            try:
                # Récupérer le chemin de destination personnalisé (optionnel)
                backup_dest = request.POST.get('backup_dest', '').strip()
                
                # Appeler la commande Django directement
                out = StringIO()
                err = StringIO()
                cmd_args = {}
                if backup_dest:
                    cmd_args['dest'] = backup_dest
                
                call_command('backup_data', **cmd_args, stdout=out, stderr=err)
                
                dest_info = f" dans {backup_dest}" if backup_dest else " dans OneDrive (par défaut)"
                messages.success(request, f"✅ Sauvegarde effectuée avec succès!{dest_info}")
                
            except Exception as e:
                messages.error(request, f"❌ Erreur lors de la sauvegarde: {str(e)}")
            
            return redirect('backups_and_recovery')
        
        elif action == 'restore_local':
            try:
                backup_file_path = request.POST.get('backup_file', '').strip()
                if not backup_file_path:
                    messages.error(request, "Aucune sauvegarde sélectionnée")
                    return redirect('backups_and_recovery')
                
                backup_path = Path(backup_file_path)
                if not backup_path.exists():
                    messages.error(request, "❌ Fichier de sauvegarde introuvable")
                    return redirect('backups_and_recovery')
                
                # Appeler la commande Django directement
                out = StringIO()
                err = StringIO()
                call_command('restore_data', str(backup_path), force=True, stdout=out, stderr=err)
                
                messages.success(request, f"✅ Restauration de {backup_path.name} effectuée avec succès!")
                
            except Exception as e:
                messages.error(request, f"❌ Erreur lors de la restauration: {str(e)}")
            
            return redirect('backups_and_recovery')
        
        elif action == 'restore':
            try:
                backup_file = request.FILES.get('backup_file')
                if not backup_file:
                    messages.error(request, "Aucun fichier sélectionné")
                    return redirect('backups_and_recovery')
                
                # Sauvegarder le fichier temporairement dans backups_local
                temp_backup = backups_dir / backup_file.name
                backups_dir.mkdir(exist_ok=True)
                
                with open(temp_backup, 'wb') as f:
                    for chunk in backup_file.chunks():
                        f.write(chunk)
                
                # Vérifier que le fichier a bien été écrit
                if not temp_backup.exists() or temp_backup.stat().st_size == 0:
                    messages.error(request, "❌ Erreur: Fichier corrompu ou vide")
                    return redirect('backups_and_recovery')
                
                # Appeler la commande Django directement
                out = StringIO()
                err = StringIO()
                call_command('restore_data', str(temp_backup), force=True, stdout=out, stderr=err)
                
                messages.success(request, "✅ Restauration effectuée avec succès!")
                
            except Exception as e:
                messages.error(request, f"❌ Erreur lors de la restauration: {str(e)}")
            
            return redirect('backups_and_recovery')
    
    context = {
        'recent_backups': recent_backups,
    }
    return render(request, 'core/backups_and_recovery.html', context)


# ===== SYSTÈME DE SAUVEGARDE AVEC BARRE DE PROGRESSION HTMX =====

# Stockage global de l'état de la sauvegarde
backup_state = {
    'status': 'idle',  # idle, running, completed, failed
    'progress': 0,
    'message': '',
    'backup_file': None,
    'backup_name': None,
    'backup_size': None,
    'error': None,
    'start_time': None,
}


def run_backup_in_background():
    """Exécute la sauvegarde en arrière-plan"""
    global backup_state
    
    try:
        backup_state['status'] = 'running'
        backup_state['progress'] = 10
        backup_state['message'] = 'Initialisation de la sauvegarde...'
        backup_state['error'] = None
        
        import subprocess
        from django.conf import settings
        
        # Info base de données
        db_name = settings.DATABASES['default']['NAME']
        db_user = settings.DATABASES['default']['USER']
        db_host = settings.DATABASES['default']['HOST']
        db_port = settings.DATABASES['default']['PORT']
        db_password = settings.DATABASES['default']['PASSWORD']
        
        # Dossier OneDrive
        backup_dir = Path(r"C:\Users\Social Media Manager\OneDrive\Torii-management\backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"backup_{db_name}_{timestamp}.sql"
        backup_gz = backup_dir / f"backup_{db_name}_{timestamp}.sql.gz"
        
        # Étape 1: Dump
        backup_state['progress'] = 20
        backup_state['message'] = 'Dump de la base de données...'
        
        env = {**dict(__import__('os').environ), 'PGPASSWORD': db_password}
        
        dump_cmd = [
            'pg_dump',
            '-h', db_host,
            '-U', db_user,
            '-p', str(db_port),
            '-Fc',
            db_name
        ]
        
        with open(backup_file, 'wb') as f:
            subprocess.run(dump_cmd, env=env, stdout=f, stderr=subprocess.PIPE, check=True)
        
        # Étape 2: Compression
        backup_state['progress'] = 70
        backup_state['message'] = 'Compression du fichier...'
        
        import gzip
        import shutil
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(backup_gz, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        backup_file.unlink()
        
        # Étape 3: Hash et métadonnées
        backup_state['progress'] = 85
        backup_state['message'] = 'Calcul de l\'intégrité...'
        
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(backup_gz, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        file_hash = sha256_hash.hexdigest()
        size_mb = backup_gz.stat().st_size / (1024 * 1024)
        
        # Créer métadonnées
        metadata = {
            'backup_file': backup_gz.name,
            'timestamp': timestamp,
            'datetime': datetime.now().isoformat(),
            'database': db_name,
            'size_bytes': backup_gz.stat().st_size,
            'hash': file_hash,
            'status': 'completed'
        }
        
        metadata_file = backup_dir / f"backup_{db_name}_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Étape 4: Succès
        backup_state['progress'] = 100
        backup_state['status'] = 'completed'
        backup_state['message'] = f'✅ Sauvegarde réussie!'
        backup_state['backup_file'] = str(backup_gz)
        backup_state['backup_name'] = backup_gz.name
        backup_state['backup_size'] = f'{size_mb:.2f} MB'
        
        # Auto-dismiss après 10 secondes
        def auto_dismiss():
            time.sleep(10)
            backup_state['status'] = 'idle'
        
        threading.Thread(target=auto_dismiss, daemon=True).start()
        
    except Exception as e:
        backup_state['status'] = 'failed'
        backup_state['error'] = str(e)
        backup_state['message'] = f'❌ Erreur: {str(e)}'


@login_required
@require_http_methods(["POST"])
def backup_start(request):
    """Démarre la sauvegarde et retourne le template de progression"""
    global backup_state
    
    # Démarrer la sauvegarde en thread
    backup_thread = threading.Thread(target=run_backup_in_background, daemon=True)
    backup_thread.start()
    
    # Retourner le template de progression
    return render(request, 'core/backup_progress.html', {
        'backup_state': backup_state
    })


@login_required
@require_http_methods(["GET"])
def backup_progress(request):
    """Retourne la progression actuelle de la sauvegarde"""
    global backup_state
    
    # Si la sauvegarde est terminée, ajouter HX-Trigger header
    response = render(request, 'core/backup_progress_bar.html', {
        'backup_state': backup_state
    })
    
    if backup_state['status'] == 'completed':
        response['HX-Trigger'] = 'done'
    elif backup_state['status'] == 'failed':
        response['HX-Trigger'] = 'done'
    
    return response


@login_required
@require_http_methods(["GET"])
def backup_result(request):
    """Affiche le résultat final de la sauvegarde"""
    global backup_state
    
    return render(request, 'core/backup_result.html', {
        'backup_state': backup_state
    })


@login_required
@require_http_methods(["GET"])
def download_schedule_pdf(request):
    """Génère et télécharge l'emploi du temps en PDF"""
    
    try:
        # Générer le PDF
        pdf_buffer = generate_schedule_pdf()
        
        if not pdf_buffer:
            messages.error(request, "❌ Aucune séance trouvée pour les 3 prochains mois")
            return redirect('dashboard')
        
        # Créer la réponse avec le PDF
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Nom du fichier
        from datetime import date
        today = date.today()
        filename = f"emploi_du_temps_{today.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la génération du PDF: {str(e)}")
        return redirect('dashboard')

