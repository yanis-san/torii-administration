from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from datetime import timedelta
from .models import Cohort, CourseSession, WeeklySchedule
from django.db.models import F
from students.models import Enrollment

@receiver(post_save, sender=Cohort)
def generate_cohort_sessions(sender, instance, created, **kwargs):
    """
    AUTOMATISME 1 : Génération Initiale
    Dès qu'on passe 'schedule_generated' à True, on crée toutes les séances.
    """
    if instance.schedule_generated and not instance.sessions.exists():
        # On récupère les patrons (ex: Lundi 10h, Jeudi 14h)
        schedules = instance.weekly_schedules.all()
        if not schedules:
            return

        current_date = instance.start_date
        sessions_to_create = []

        # Boucle jour par jour jusqu'à la fin
        while current_date <= instance.end_date:
            weekday = current_date.weekday() # 0=Lundi, 6=Dimanche
            
            # Est-ce qu'il y a cours ce jour-là ?
            for sched in schedules:
                if sched.day_of_week == weekday:
                    sessions_to_create.append(
                        CourseSession(
                            cohort=instance,
                            date=current_date,
                            start_time=sched.start_time,
                            end_time=sched.end_time,
                            teacher=instance.teacher,
                            classroom=sched.classroom,
                            status='SCHEDULED'
                        )
                    )
            current_date += timedelta(days=1)
        
        # Insertion en masse (Performant)
        CourseSession.objects.bulk_create(sessions_to_create)

@receiver(post_save, sender=CourseSession)
def handle_session_changes(sender, instance, created, **kwargs):
    """
    AUTOMATISME 2 : Gestion des imprévus (Report)
    Si une séance passe à 'POSTPONED', on crée AUTOMATIQUEMENT un rattrapage à la fin.
    """
    if created:
        return # On ne fait rien à la création initiale

    # On utilise un tracker pour savoir si le champ status a changé (optionnel, 
    # ici on suppose qu'on vérifie juste l'état actuel pour simplifier)
    
    if instance.status == 'POSTPONED':
        # 1. Vérifier si un rattrapage existe déjà pour éviter les boucles infinies
        # On regarde s'il existe une séance future avec une note liant à celle-ci
        already_rescheduled = CourseSession.objects.filter(
            cohort=instance.cohort,
            note__contains=f"Rattrapage séance du {instance.date}"
        ).exists()

        if not already_rescheduled:
            with transaction.atomic():
                # Trouver la toute dernière séance du groupe
                last_session = instance.cohort.sessions.order_by('-date').first()
                
                # Règle simple : On propose la date 1 semaine après la dernière séance
                # (Ou le lendemain, selon ta règle métier préférée)
                new_date = last_session.date + timedelta(days=7)
                
                CourseSession.objects.create(
                    cohort=instance.cohort,
                    date=new_date,
                    start_time=instance.start_time,
                    end_time=instance.end_time,
                    teacher=instance.teacher,
                    classroom=instance.classroom,
                    status='SCHEDULED',
                    note=f"AUTO: Rattrapage séance du {instance.date}"
                )
                
                # IMPORTANT : On met à jour la date de fin du groupe pour refléter la réalité
                cohort = instance.cohort
                if new_date > cohort.end_date:
                    cohort.end_date = new_date
                    # On sauvegarde sans redéclencher le signal de génération (il check .exists())
                    cohort.save()


@receiver(post_save, sender=CourseSession)
def update_student_hours(sender, instance, created, **kwargs):
    """
    AUTOMATISME 3 : Débit des heures (Pack)
    Quand une séance est terminée, on ajoute la durée aux 'heures consommées' 
    de tous les étudiants inscrits dans ce groupe.
    """
    if instance.status == 'COMPLETED':
        # 1. Calculer la durée en heures (ex: 1.5)
        duration_minutes = (instance.end_time.hour * 60 + instance.end_time.minute) - \
                           (instance.start_time.hour * 60 + instance.start_time.minute)
        duration_hours = duration_minutes / 60.0

        # 2. Trouver les élèves ACTIFS de ce groupe
        # On utilise F() pour une mise à jour atomique (évite les conflits)
        Enrollment.objects.filter(
            cohort=instance.cohort, 
            is_active=True
        ).update(hours_consumed=F('hours_consumed') + duration_hours)