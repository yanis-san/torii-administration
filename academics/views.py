from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from students.models import Enrollment, Attendance
from .models import Cohort, CourseSession
from datetime import datetime, date, timedelta
from django.db.models import Count, Q
from core.models import AcademicYear, User


def cohort_list(request):
    """
    Liste de tous les groupes (cohortes) avec filtres.
    """
    cohorts = Cohort.objects.select_related(
        'subject', 'level', 'teacher', 'academic_year'
    ).prefetch_related('enrollments').annotate(
        remaining=Count('sessions', filter=Q(sessions__status__in=['SCHEDULED', 'POSTPONED']))
    ).all().order_by('-start_date')

    # Filtres
    year_filter = request.GET.get('year', '')  # id de l'année académique
    # Par défaut, filtrer sur l'année académique courante (is_current=True)
    if not year_filter:
        current_year = AcademicYear.objects.filter(is_current=True).first()
        if current_year:
            year_filter = str(current_year.id)
    if year_filter:
        cohorts = cohorts.filter(academic_year__id=year_filter)

    status_filter = request.GET.get('status', '')  # 'finished' | 'ongoing'
    if status_filter == 'finished':
        cohorts = cohorts.filter(remaining=0)
    elif status_filter == 'ongoing':
        cohorts = cohorts.filter(remaining__gt=0)

    modality_filter = request.GET.get('modality', '')  # 'ONLINE' | 'IN_PERSON'
    if modality_filter in ['ONLINE', 'IN_PERSON']:
        cohorts = cohorts.filter(modality=modality_filter)

    individual_filter = request.GET.get('individual', '')  # '1' | '0'
    if individual_filter == '1':
        cohorts = cohorts.filter(is_individual=True)
    elif individual_filter == '0':
        cohorts = cohorts.filter(is_individual=False)

    years = AcademicYear.objects.all().order_by('-start_date')
    auto_year_default = False
    if request.GET.get('year', '') == '' and year_filter:
        auto_year_default = True

    context = {
        'cohorts': cohorts,
        'status_filter': status_filter,
        'year_filter': year_filter,
        'auto_year_default': auto_year_default,
        'modality_filter': modality_filter,
        'individual_filter': individual_filter,
        'years': years,
    }
    return render(request, 'academics/cohort_list.html', context)


def cohort_detail(request, pk):
    """
    Page de détail d'un groupe avec le calendrier complet des séances.
    """
    cohort = get_object_or_404(Cohort, pk=pk)

    # Formulaire léger pour configurer le mode Ramadan sans passer par l'admin
    if request.method == 'POST':
        try:
            rs = (request.POST.get('ramadan_start') or '').strip()
            re = (request.POST.get('ramadan_end') or '').strip()
            rst = (request.POST.get('ramadan_start_time') or '').strip()
            ret = (request.POST.get('ramadan_end_time') or '').strip()
            rrate = (request.POST.get('ramadan_teacher_hourly_rate') or '').strip()

            cohort.ramadan_start = datetime.strptime(rs, '%Y-%m-%d').date() if rs else None
            cohort.ramadan_end = datetime.strptime(re, '%Y-%m-%d').date() if re else None
            cohort.ramadan_start_time = datetime.strptime(rst, '%H:%M').time() if rst else None
            cohort.ramadan_end_time = datetime.strptime(ret, '%H:%M').time() if ret else None
            cohort.ramadan_teacher_hourly_rate = int(rrate) if rrate else None

            cohort.save(update_fields=[
                'ramadan_start', 'ramadan_end', 'ramadan_start_time', 'ramadan_end_time',
                'ramadan_teacher_hourly_rate'
            ])
            messages.success(request, "Paramètres Ramadan enregistrés pour ce groupe.")
            return redirect('academics:detail', pk=cohort.id)
        except ValueError:
            messages.error(request, "Valeurs invalides pour les dates/heures Ramadan.")
            return redirect('academics:detail', pk=cohort.id)

    # Récupérer toutes les séances du groupe
    sessions = cohort.sessions.select_related('teacher', 'classroom').order_by('date', 'start_time')
    remaining_sessions = sessions.filter(status__in=['SCHEDULED', 'POSTPONED']).count()

    # Récupérer les inscriptions actives
    enrollments = cohort.enrollments.filter(is_active=True).select_related('student')

    # Statistiques rapides
    total_sessions = sessions.count()
    completed_sessions = sessions.filter(status='COMPLETED').count()
    upcoming_sessions = sessions.filter(date__gte=date.today(), status='SCHEDULED').count()

    context = {
        'cohort': cohort,
        'sessions': sessions,
        'enrollments': enrollments,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'upcoming_sessions': upcoming_sessions,
        'remaining_sessions': remaining_sessions,
        'today': date.today(),
    }
    return render(request, 'academics/cohort_detail.html', context)


def generate_sessions(request, pk):
    """
    Vue HTMX pour déclencher la génération automatique des séances.
    Met à jour le flag schedule_generated=True, ce qui déclenche le Signal.
    """
    if request.method == 'POST':
        cohort = get_object_or_404(Cohort, pk=pk)
        # 1) Vérifier qu'il y a bien des créneaux hebdomadaires
        schedules = list(cohort.weekly_schedules.all())
        if not schedules:
            return HttpResponse(
                "<div class='text-red-600 font-bold'>Aucun créneau hebdomadaire (WeeklySchedule) n'est défini pour ce groupe. Créez-en d'abord dans l'admin.</div>"
            )
        # 2) Nettoyer les séances au-delà de la nouvelle end_date (uniquement les non réalisées)
        cohort.sessions.filter(date__gt=cohort.end_date, status__in=['SCHEDULED', 'POSTPONED']).delete()

        # 3) Génération incrémentale : on crée seulement les séances manquantes
        existing_sessions = list(cohort.sessions.all())
        existing_keys = {
            (s.date, s.start_time, s.end_time, s.classroom_id) for s in existing_sessions
        }

        current_date = cohort.start_date
        sessions_to_create = []

        while current_date <= cohort.end_date:
            weekday = current_date.weekday()  # 0 = Lundi
            for sched in schedules:
                if sched.day_of_week != weekday:
                    continue
                key = (current_date, sched.start_time, sched.end_time, sched.classroom_id)
                if key in existing_keys:
                    continue
                sessions_to_create.append(
                    CourseSession(
                        cohort=cohort,
                        date=current_date,
                        start_time=sched.start_time,
                        end_time=sched.end_time,
                        teacher=cohort.teacher,
                        classroom=sched.classroom,
                        status='SCHEDULED'
                    )
                )
                existing_keys.add(key)
            current_date += timedelta(days=1)

        if sessions_to_create:
            CourseSession.objects.bulk_create(sessions_to_create)

        cohort.schedule_generated = True
        cohort.save(update_fields=['schedule_generated'])

        if sessions_to_create:
            messages.success(request, f"Planning complété pour {cohort.name} : {len(sessions_to_create)} nouvelles séances ajoutées.")
        else:
            messages.info(request, f"Planning déjà complet pour {cohort.name} sur la plage actuelle.")

        # Rediriger vers la page de détail
        return redirect('academics:detail', pk=cohort.id)

    return HttpResponse(status=405)  # Method Not Allowed


def finish_cohort(request, pk):
    """Supprime les séances non terminées et fixe la date de fin à aujourd'hui."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    cohort = get_object_or_404(Cohort, pk=pk)

    pending_qs = cohort.sessions.filter(status__in=['SCHEDULED', 'POSTPONED'])
    deleted_count = pending_qs.count()
    pending_qs.delete()

    today_date = date.today()
    cohort.end_date = today_date
    cohort.schedule_generated = False
    cohort.save(update_fields=['end_date', 'schedule_generated'])

    messages.success(
        request,
        f"Groupe clôturé : {deleted_count} séance(s) non terminée(s) supprimée(s). Date de fin fixée au {today_date.strftime('%d/%m/%Y')}.",
    )

    return redirect('academics:detail', pk=cohort.id)


def session_detail(request, session_id):
    """
    Page de gestion de la présence (Faire l'appel).
    GET : Affiche le formulaire avec les présences actuelles
    POST : Enregistre les statuts de présence + note de séance
    """
    session = get_object_or_404(
        CourseSession.objects.select_related('cohort', 'teacher', 'classroom'),
        id=session_id
    )

    # Récupérer toutes les inscriptions actives du groupe
    enrollments = session.cohort.enrollments.filter(is_active=True).select_related('student')

    # Récupérer les présences existantes pour cette séance
    attendances = Attendance.objects.filter(session=session).select_related('student')

    # Créer un dictionnaire {student_id: status} pour pré-remplir le formulaire
    attendance_dict = {att.student.id: att.status for att in attendances}

    # Calcul de la rémunération du prof (utilise override si présent)
    duration_hours = float(session.duration_hours)
    teacher_pay = float(session.pay_amount)

    # Mode édition si demandé explicitement en GET (?edit=1)
    is_editing = request.GET.get('edit') == '1'

    if request.method == 'POST':
        # Verrou: si le groupe est terminé, on bloque toute modification
        if session.cohort.is_finished:
            messages.error(request, "Groupe terminé : modifications verrouillées.")
            return redirect('academics:detail', pk=session.cohort.id)
        
        # 0. Gérer le choix du professeur (nouveau)
        teacher_id = request.POST.get('teacher_id', '')
        if teacher_id:
            try:
                new_teacher = User.objects.get(id=int(teacher_id), is_teacher=True)
                # Vérifier que c'est le titulaire ou un des remplaçants
                if new_teacher == session.cohort.teacher or new_teacher in session.cohort.substitute_teachers.all():
                    session.teacher = new_teacher
                    messages.info(request, f"Professeur changé à {new_teacher.get_full_name()}")
                else:
                    messages.error(request, "Ce professeur n'est pas autorisé pour ce groupe.")
            except (User.DoesNotExist, ValueError):
                messages.error(request, "Professeur invalide.")
        
        # 0.5 Gérer la modification du taux horaire override
        new_hourly_rate = request.POST.get('teacher_hourly_rate_override', '').strip()
        if new_hourly_rate:
            try:
                new_hourly_rate = int(new_hourly_rate)
                if new_hourly_rate > 0:
                    session.teacher_hourly_rate_override = new_hourly_rate
                    messages.info(request, f"Taux horaire de cette séance modifié à {new_hourly_rate} DA/h")
                else:
                    messages.error(request, "Le taux horaire doit être un nombre positif.")
            except ValueError:
                messages.error(request, "Taux horaire invalide.")
        elif new_hourly_rate == '':
            # Si vide, supprimer la surcharge
            if session.teacher_hourly_rate_override is not None:
                session.teacher_hourly_rate_override = None
                messages.info(request, f"Taux horaire remis au taux standard du cohort ({session.cohort.teacher_hourly_rate} DA/h)")
        
        # Traitement du formulaire (reste inchangé)
        try:
            # 1. Gérer le changement de créneau horaire (NOUVEAU)
            custom_start_time = request.POST.get('custom_start_time', '').strip()
            custom_end_time = request.POST.get('custom_end_time', '').strip()
            
            if custom_start_time and custom_end_time:
                from datetime import datetime, time as dt_time
                try:
                    # Parser les heures
                    new_start = datetime.strptime(custom_start_time, '%H:%M').time()
                    new_end = datetime.strptime(custom_end_time, '%H:%M').time()
                    
                    # Vérifier que l'heure de fin est après l'heure de début
                    if new_end > new_start:
                        session.start_time = new_start
                        session.end_time = new_end
                        # Calculer la nouvelle durée
                        from datetime import datetime as dt, date
                        duration = dt.combine(date.today(), new_end) - dt.combine(date.today(), new_start)
                        new_duration_hours = duration.total_seconds() / 3600
                        messages.info(request, f"Créneau horaire modifié : {new_start.strftime('%H:%M')} - {new_end.strftime('%H:%M')} ({new_duration_hours:.1f}h)")
                    else:
                        messages.warning(request, "L'heure de fin doit être après l'heure de début.")
                except ValueError:
                    messages.warning(request, "Format d'heure invalide.")
            
            # 2. Enregistrer la note de séance
            session_note = request.POST.get('session_note', '')
            session.note = session_note

            # 3. Marquer la séance comme COMPLETED
            session.status = 'COMPLETED'
            session.save()

            # 4. Mettre à jour les présences (PRESENT/ABSENT uniquement)
            for enrollment in enrollments:
                student_id = enrollment.student.id
                status_key = f"status_{student_id}"
                new_status = request.POST.get(status_key, 'PRESENT')
                if new_status not in ['PRESENT', 'ABSENT']:
                    new_status = 'PRESENT'

                # Mettre à jour ou créer l'Attendance
                # On match uniquement sur session et student (contrainte unique)
                Attendance.objects.update_or_create(
                    session=session,
                    student=enrollment.student,
                    defaults={
                        'status': new_status,
                        'enrollment': enrollment
                    }
                )

            messages.success(request, f"Séance validée avec succès !")
            # Après validation, on revient à la page du groupe.
            return redirect('academics:detail', pk=session.cohort.id)

        except Exception as e:
            messages.error(request, f"Erreur lors de la validation : {str(e)}")

    context = {
        'session': session,
        'enrollments': enrollments,
        'attendance_dict': attendance_dict,
        'teacher_pay': teacher_pay,
        'duration_hours': round(duration_hours, 2),
        'is_editing': is_editing,
        'available_teachers': [session.cohort.teacher] + list(session.cohort.substitute_teachers.all()),
        'hourly_rate_override': session.teacher_hourly_rate_override,
        'standard_hourly_rate': session.cohort.teacher_hourly_rate,
        'current_hourly_rate': session.pay_hourly_rate,
    }
    return render(request, 'academics/session_detail.html', context)


def postpone_session(request, session_id):
    """
    Marque une séance comme reportée (POSTPONED).
    Le signal handle_session_changes créera automatiquement un rattrapage.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    session = get_object_or_404(CourseSession, id=session_id)

    # Si déjà annulée ou reportée, on évite les doublons
    if session.status in ['POSTPONED', 'CANCELLED']:
        messages.info(request, "Cette séance est déjà reportée ou annulée.")
        return redirect('academics:detail', pk=session.cohort.id)

    session.status = 'POSTPONED'
    session.note = (session.note or '') + "\n[Auto] Séance reportée via bouton." if session.note else "[Auto] Séance reportée via bouton."
    session.save()

    messages.success(request, "Séance marquée comme reportée. Un rattrapage sera ajouté automatiquement.")
    return redirect('academics:detail', pk=session.cohort.id)


def cancel_postpone(request, session_id):
    """
    Annule le report d'une séance : remet en SCHEDULED et supprime le rattrapage créé.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    session = get_object_or_404(CourseSession, id=session_id)

    if session.status != 'POSTPONED':
        messages.warning(request, "Cette séance n'est pas reportée.")
        return redirect('academics:detail', pk=session.cohort.id)

    # Remettre en Prévu
    session.status = 'SCHEDULED'
    # Nettoyer la note automatique
    if "[Auto] Séance reportée via bouton." in (session.note or ''):
        session.note = session.note.replace("[Auto] Séance reportée via bouton.", "").strip()
    session.save()

    # Supprimer le rattrapage créé (identifié par la note contenant la date de cette séance)
    makeup_session = CourseSession.objects.filter(
        cohort=session.cohort,
        note__contains=f"Rattrapage séance du {session.date}"
    ).first()

    if makeup_session:
        makeup_session.delete()
        messages.success(request, "Report annulé. La séance est remise en 'Prévu' et le rattrapage supprimé.")
    else:
        messages.info(request, "Report annulé. Aucune séance de rattrapage automatique trouvée à supprimer.")

    return redirect('academics:detail', pk=session.cohort.id)


def change_session_teacher(request, session_id):
    """
    Permet de changer le professeur d'une séance spécifique.
    GET : Affiche le formulaire avec la liste des profs actifs
    POST : Enregistre le nouveau prof et note le changement
    """
    from core.models import User
    
    session = get_object_or_404(
        CourseSession.objects.select_related('cohort', 'teacher', 'classroom'),
        id=session_id
    )
    
    # Liste de tous les professeurs actifs
    all_teachers = User.objects.filter(is_teacher=True, is_active=True).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        new_teacher_id = request.POST.get('teacher_id')
        if not new_teacher_id:
            messages.error(request, "Veuillez sélectionner un professeur.")
            return redirect('academics:change_session_teacher', session_id=session_id)
        
        new_teacher = get_object_or_404(User, id=new_teacher_id, is_teacher=True)
        old_teacher = session.teacher
        
        # Mettre à jour le professeur
        session.teacher = new_teacher
        
        # Ajouter une note pour traçabilité
        change_note = f"\n[Changement prof: {old_teacher.get_full_name()} → {new_teacher.get_full_name()}]"
        session.note = (session.note or '') + change_note
        session.save()
        
        messages.success(
            request, 
            f"Professeur changé avec succès. Cette séance sera payée à {new_teacher.get_full_name()}."
        )
        return redirect('academics:detail', pk=session.cohort.id)
    
    context = {
        'session': session,
        'all_teachers': all_teachers,
        'cohort_teacher': session.cohort.teacher,
        'substitute_teacher': session.cohort.substitute_teacher,
    }
    return render(request, 'academics/change_session_teacher.html', context)


def add_session_manual(request, cohort_id):
    """
    Ajouter une séance manuellement via formulaire.
    Si date/heure ne sont pas remplies, propose automatiquement la prochaine séance
    selon le planning hebdomadaire (WeeklySchedule).
    Pré-remplit aussi la salle et prof selon le créneau planifié.
    """
    from .forms import CourseSessionForm
    from datetime import datetime
    
    cohort = get_object_or_404(Cohort, pk=cohort_id)
    next_scheduled = None
    
    if request.method == 'POST':
        form = CourseSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.cohort = cohort
            
            # Si date/heure ne sont pas remplies, utiliser le planning automatique
            if not session.date or not session.start_time or not session.end_time:
                next_slot = cohort.get_next_scheduled_session_time()
                if next_slot:
                    session.date = next_slot['date']
                    session.start_time = next_slot['start_time']
                    session.end_time = next_slot['end_time']
                    # Assigner la salle du créneau aussi
                    if next_slot['classroom']:
                        session.classroom = next_slot['classroom']
                else:
                    messages.error(request, "Impossible de déterminer la prochaine séance. Veuillez saisir manuellement la date et les horaires.")
                    # Garder le formulaire avec les données saisies
                    context = {
                        'cohort': cohort,
                        'form': form,
                        'page_title': f'Ajouter une séance - {cohort.name}',
                    }
                    return render(request, 'academics/add_session.html', context)
            
            session.save()
            # Formater la date et l'heure correctement en Python
            date_str = session.date.strftime('%d/%m/%Y')
            time_str = session.start_time.strftime('%H:%M')
            messages.success(request, f"Séance du {date_str} à {time_str} ajoutée avec succès !")
            return redirect('academics:detail', pk=cohort.id)
    else:
        # Calculer la prochaine séance selon le planning
        next_scheduled = cohort.get_next_scheduled_session_time()
        
        # Pré-remplir avec des valeurs par défaut
        initial_data = {
            'status': 'SCHEDULED',
            'teacher': cohort.teacher,
        }
        
        # Si un créneau a été trouvé, le proposer
        if next_scheduled:
            initial_data.update({
                'date': next_scheduled['date'],
                'start_time': next_scheduled['start_time'],
                'end_time': next_scheduled['end_time'],
                'classroom': next_scheduled['classroom'],
            })
        
        form = CourseSessionForm(initial=initial_data)
    
    # Filtrer les professeurs disponibles
    form.fields['teacher'].queryset = form.fields['teacher'].queryset.filter(is_teacher=True)
    
    context = {
        'cohort': cohort,
        'form': form,
        'page_title': f'Ajouter une séance - {cohort.name}',
        'next_scheduled': next_scheduled,
    }
    return render(request, 'academics/add_session.html', context)
