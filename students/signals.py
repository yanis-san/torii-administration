from django.db.models.signals import post_save, post_delete
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from .models import Enrollment, Attendance, StudentAnnualFee, Student
from core.models import AcademicYear
from academics.models import CourseSession

# --- AUTOMATISME 1 : Inscription -> Génération Présence Future ---
@receiver(post_save, sender=Enrollment)
def create_attendance_for_new_enrollment(sender, instance, created, **kwargs):
    """
    Quand un élève s'inscrit, on l'ajoute automatiquement 
    à toutes les séances FUTURES du groupe.
    """
    if kwargs.get('raw', False):
        return

    if created and instance.is_active:
        # S'assurer qu'une fiche de frais annuelle existe pour l'année active (état par défaut: non payé)
        current_year = AcademicYear.get_current()
        if current_year and not StudentAnnualFee.objects.filter(student=instance.student, academic_year=current_year).exists():
            StudentAnnualFee.objects.create(
                student=instance.student,
                academic_year=current_year,
                amount=1000,
                is_paid=False
            )

        # Récupérer les séances à venir
        future_sessions = CourseSession.objects.filter(
            cohort=instance.cohort,
            date__gte=timezone.now().date()
        )
        
        attendances = []
        for session in future_sessions:
            # On vérifie pour éviter les doublons
            if not Attendance.objects.filter(session=session, student=instance.student).exists():
                attendances.append(Attendance(
                    session=session,
                    student=instance.student,
                    enrollment=instance,
                    status='PRESENT', # On présume qu'il sera là
                    billable=True     # Par défaut, c'est facturable
                ))
        
        if attendances:
            Attendance.objects.bulk_create(attendances)


# --- AUTOMATISME 1.bis : Générer le code contrat après création ---
@receiver(post_save, sender=Enrollment)
def generate_contract_code_on_create(sender, instance: Enrollment, created, **kwargs):
    """Assigne un code contrat unique à l'inscription nouvellement créée."""
    try:
        if (created or not instance.contract_code) and instance.id and not instance.contract_code:
            code = instance.generate_contract_code()
            # Eviter collisions: si déjà pris, fallback avec suffixe id
            from django.db.models import Q
            exists = Enrollment.objects.filter(Q(contract_code=code) & ~Q(id=instance.id)).exists()
            if exists:
                code = f"{code}-{instance.id}"
            Enrollment.objects.filter(id=instance.id).update(contract_code=code)
    except Exception:
        # Ne pas casser la création si le code échoue
        pass

# --- AUTOMATISME 2 : Nouvelle Séance -> Ajout des Élèves Inscrits ---
@receiver(post_save, sender=CourseSession)
def create_attendance_for_new_session(sender, instance, created, **kwargs):
    """
    Quand une séance est créée (ou reportée/générée), 
    on crée les lignes de présence pour tous les élèves ACTIFS.
    """
    if kwargs.get('raw', False):
        return

    if created:
        active_enrollments = Enrollment.objects.filter(
            cohort=instance.cohort,
            is_active=True
        )
        
        attendances = []
        for enrollment in active_enrollments:
            attendances.append(Attendance(
                session=instance,
                student=enrollment.student,
                enrollment=enrollment,
                status='PRESENT',
                billable=True
            ))
        
        if attendances:
            Attendance.objects.bulk_create(attendances)

# --- AUTOMATISME 3 : Modification Présence -> Recalcul Heures Consommées ---
@receiver(post_save, sender=Attendance)
def recalculate_hours_consumed(sender, instance, **kwargs):
    """
    Recalcule les heures consommées basé sur le champ 'billable'.
    Permet de facturer une absence non excusée ou d'offrir une séance.
    """
    enrollment = instance.enrollment
    
    # Si ce n'est pas un pack d'heures, on s'en fiche
    if enrollment.payment_plan != 'PACK':
        return

    # ON PREND TOUT CE QUI EST "FACTURABLE" (billable=True)
    # Peu importe si le statut est 'PRESENT', 'ABSENT' ou 'LATE'
    charged_attendances = Attendance.objects.filter(
        enrollment=enrollment,
        billable=True
    ).filter(
        Q(session__status='COMPLETED') | Q(status='PRESENT')
    ).select_related('session')
    
    total_hours = 0
    for att in charged_attendances:
        # Durée effective (prend en compte un éventuel override)
        total_hours += float(att.session.duration_hours)
    
    # Mise à jour directe du champ sur l'inscription
    enrollment.hours_consumed = total_hours
    enrollment.save(update_fields=['hours_consumed'])

# --- AUTOMATISME 4 : Surcharge durée séance -> Recalcul heures PACK ---
@receiver(post_save, sender=CourseSession)
def recalc_pack_hours_on_session_change(sender, instance, **kwargs):
    """Si une séance change (override, horaires, etc.),
    recalculer les heures consommées des inscriptions PACK concernées."""
    # Trouver les attendances liées à cette séance et facturables
    related_attendances = Attendance.objects.filter(session=instance, billable=True, session__status='COMPLETED').select_related('enrollment')

    # Recalculer par inscription PACK
    seen = set()
    for att in related_attendances:
        enrollment = att.enrollment
        if enrollment.id in seen:
            continue
        seen.add(enrollment.id)
        if enrollment.payment_plan != 'PACK':
            continue

        charged_attendances = Attendance.objects.filter(
            enrollment=enrollment,
            billable=True,
            session__status='COMPLETED'
        ).select_related('session')

        total_hours = 0
        for a in charged_attendances:
            total_hours += float(a.session.duration_hours)

        enrollment.hours_consumed = total_hours
        enrollment.save(update_fields=['hours_consumed'])

# --- AUTOMATISME : Suppression étudiant -> Remettre prospect à 'À convertir' ---
@receiver(post_delete, sender=Student)
def reset_prospect_on_student_delete(sender, instance, **kwargs):
    """
    Quand un étudiant est supprimé, chercher le prospect correspondant (même email)
    et remettre converted=False pour qu'il réapparaisse comme 'À convertir'
    """
    if instance.email:
        from prospects.models import Prospect
        Prospect.objects.filter(email=instance.email, converted=True).update(converted=False)


# --- AUTOMATISME : Création étudiant -> Marquer prospect comme converti ---
@receiver(post_save, sender=Student)
def mark_prospect_as_converted(sender, instance, created, **kwargs):
    """
    Quand un étudiant est créé avec succès, marquer le prospect correspondant 
    (même email) comme converti=True
    """
    if created and instance.email:
        from prospects.models import Prospect
        Prospect.objects.filter(email=instance.email, converted=False).update(converted=True)
