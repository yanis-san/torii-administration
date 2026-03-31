from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Payment
from django.http import HttpResponse

def apply_group_discount(cohort_id, discount_id):
    """Applique une réduction à TOUS les étudiants d'un groupe"""
    cohort = Cohort.objects.get(id=cohort_id)
    discount = Discount.objects.get(id=discount_id)
    
    enrollments = Enrollment.objects.filter(cohort=cohort, is_active=True)
    
    for enrollment in enrollments:
        enrollment.discount = discount
        # On force le recalcul (en remettant agreed_amount à None ou via une méthode update)
        # Attention : Si l'étudiant a déjà payé, c'est délicat. 
        # Ici on suppose qu'on applique ça au début.
        
        base = cohort.standard_price
        if discount.type == 'FIXED':
            new_price = base - discount.value
        else:
            new_price = base - (base * (discount.value / 100))
            
        enrollment.agreed_amount = new_price
        enrollment.save()



from django.shortcuts import render, redirect, get_object_or_404
from students.models import Enrollment
from .forms import PaymentForm

def add_payment(request, enrollment_id):
    # On récupère le contrat spécifique (ex: Chinois de Lina)
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        
        if form.is_valid():
            payment = form.save(commit=False)
            payment.enrollment = enrollment
            payment.recorded_by = request.user # L'admin connecté
            payment.save()
            
            messages.success(request, f"✅ Paiement de {payment.amount} DA enregistré avec succès!")
            return redirect('students:detail', pk=enrollment.student.id)
        else:
            messages.error(request, "Erreur lors de la validation du formulaire. Veuillez vérifier les champs.")
    else:
        # On pré-remplit avec le reste à payer (Balance Due)
        form = PaymentForm(initial={'amount': enrollment.balance_due})

    context = {
        'form': form,
        'enrollment': enrollment,
        'student': enrollment.student
    }
    return render(request, 'finance/payment_form.html', context)


def delete_payment(request, payment_id):
    """Supprimer un paiement (POST only)"""
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    payment = get_object_or_404(Payment, pk=payment_id)
    student_id = payment.enrollment.student.id
    
    # Supprimer le fichier si il existe
    if payment.receipt:
        payment.receipt.delete()
    
    payment.delete()
    messages.success(request, f"Paiement de {payment.amount} DA supprimé avec succès.")
    
    return redirect('students:detail', pk=student_id)


def edit_payment(request, payment_id):
    """Modifier un paiement existant (montant, méthode, référence, reçu)."""
    payment = get_object_or_404(Payment, pk=payment_id)
    enrollment = payment.enrollment

    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            # Si un nouveau reçu est uploadé, Django remplacera le fichier;
            # pour éviter les fichiers orphelins, on supprime l'ancien si nécessaire.
            if 'receipt' in request.FILES and payment.receipt:
                try:
                    old = payment.receipt
                    # On ne supprime qu'après sauvegarde réussie; on retient la référence
                except Exception:
                    old = None

            updated = form.save()

            # Nettoyage éventuel de l'ancien reçu (si remplacé)
            if 'receipt' in request.FILES:
                try:
                    if old and old.name != updated.receipt.name:
                        old.delete(save=False)
                except Exception:
                    pass

            messages.success(request, "Paiement mis à jour avec succès.")
            return redirect('students:detail', pk=enrollment.student.id)
        else:
            messages.error(request, "Erreur lors de la validation du formulaire. Veuillez vérifier les champs.")
    else:
        form = PaymentForm(instance=payment)

    context = {
        'form': form,
        'payment': payment,
        'enrollment': enrollment,
        'student': enrollment.student,
        'is_edit': True,
    }
    return render(request, 'finance/payment_edit.html', context)


# =====================================================
# GESTION DE LA PAIE DES PROFESSEURS (PAYROLL SYSTEM)
# =====================================================

from django.db.models import Sum, F, ExpressionWrapper, DurationField
from datetime import datetime, timedelta, date
from core.models import User, TeacherProfile
from academics.models import CourseSession
from .models import TeacherPayment
from django.contrib import messages


def teacher_payroll_list(request):
    """
    Vue principale : Liste des professeurs avec calcul de la paie due.
    Affiche pour chaque prof : heures travaillées, montant dû, méthode préférée.
    """
    # Récupérer tous les professeurs
    teachers = User.objects.filter(is_teacher=True).select_related('teacher_profile')

    # Récupérer les filtres de période (SANS filtre par défaut - optionnel)
    period_start = request.GET.get('start')
    period_end = request.GET.get('end')
    
    if period_start and period_end:
        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
    else:
        # Pas de filtrage par date par défaut
        period_start = None
        period_end = None

    payroll_data = []

    for teacher in teachers:
        # Récupérer les séances COMPLETED
        sessions_query = CourseSession.objects.filter(
            teacher=teacher,
            status='COMPLETED'
        )
        
        # Appliquer le filtre de date si fourni
        if period_start and period_end:
            sessions_query = sessions_query.filter(
                date__gte=period_start,
                date__lte=period_end
            )
        
        sessions = sessions_query.select_related('cohort')

        # Calculer les heures travaillées et le montant total
        total_hours = 0
        total_amount = 0

        for session in sessions:
            # Utiliser la durée effective (override si défini)
            hours = float(session.duration_hours)

            # Montant pour cette séance (utilise le taux override s'il existe)
            session_pay = hours * float(session.pay_hourly_rate)

            total_hours += hours
            total_amount += session_pay

        # Vérifier si déjà payé pour cette période
        already_paid_query = TeacherPayment.objects.filter(teacher=teacher)
        if period_start and period_end:
            already_paid_query = already_paid_query.filter(
                period_start=period_start,
                period_end=period_end
            )
        
        already_paid = already_paid_query.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        # Récupérer le profil (ou None si pas créé)
        profile = getattr(teacher, 'teacher_profile', None)

        payroll_data.append({
            'teacher': teacher,
            'profile': profile,
            'total_hours': round(total_hours, 2),
            'total_amount': round(total_amount, 2),
            'already_paid': float(already_paid),
            'balance_due': round(total_amount - float(already_paid), 2),
            'sessions_count': sessions.count(),
        })

    context = {
        'payroll_data': payroll_data,
        'period_start': period_start,
        'period_end': period_end,
    }
    return render(request, 'finance/teacher_payroll_list.html', context)


def teacher_payroll_detail(request, teacher_id):
    """
    Détail d'un professeur : historique des paiements + séances de la période actuelle.
    """
    teacher = get_object_or_404(User, id=teacher_id, is_teacher=True)

    # Récupérer la période depuis les paramètres GET
    today = date.today()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_last_month = today.replace(day=1) - timedelta(days=1)

    period_start = request.GET.get('start', first_day_last_month.strftime('%Y-%m-%d'))
    period_end = request.GET.get('end', last_day_last_month.strftime('%Y-%m-%d'))

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()

    # Récupérer les séances complétées pour cette période
    sessions = CourseSession.objects.filter(
        teacher=teacher,
        status='COMPLETED',
        date__gte=period_start,
        date__lte=period_end
    ).select_related('cohort', 'classroom').order_by('date', 'start_time')

    # Calculer le détail
    session_details = []
    total_hours = 0
    total_amount = 0

    for session in sessions:
        hours = float(session.duration_hours)
        pay = hours * float(session.pay_hourly_rate)

        session_details.append({
            'session': session,
            'hours': round(hours, 2),
            'hourly_rate': float(session.pay_hourly_rate),
            'pay': round(pay, 2),
        })

        total_hours += hours
        total_amount += pay

    # Historique des paiements (tous)
    payment_history = TeacherPayment.objects.filter(teacher=teacher).order_by('-payment_date')

    # Profil du prof
    profile = getattr(teacher, 'teacher_profile', None)

    context = {
        'teacher': teacher,
        'profile': profile,
        'period_start': period_start,
        'period_end': period_end,
        'session_details': session_details,
        'total_hours': round(total_hours, 2),
        'total_amount': round(total_amount, 2),
        'payment_history': payment_history,
    }
    return render(request, 'finance/teacher_payroll_detail.html', context)


def record_teacher_payment(request, teacher_id):
    """
    Formulaire pour enregistrer un paiement de salaire.
    Pré-remplit avec la méthode préférée du prof et le montant dû.
    """
    teacher = get_object_or_404(User, id=teacher_id, is_teacher=True)

    # Récupérer la période depuis les paramètres GET
    today = date.today()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_last_month = today.replace(day=1) - timedelta(days=1)

    period_start_str = request.GET.get('start', first_day_last_month.strftime('%Y-%m-%d'))
    period_end_str = request.GET.get('end', last_day_last_month.strftime('%Y-%m-%d'))
    amount_due = request.GET.get('amount', '0')

    if request.method == 'POST':
        try:
            # Créer le paiement
            payment = TeacherPayment.objects.create(
                teacher=teacher,
                period_start=datetime.strptime(request.POST.get('period_start'), '%Y-%m-%d').date(),
                period_end=datetime.strptime(request.POST.get('period_end'), '%Y-%m-%d').date(),
                total_amount=request.POST.get('total_amount'),
                payment_method=request.POST.get('payment_method'),
                payment_date=datetime.strptime(request.POST.get('payment_date'), '%Y-%m-%d').date(),
                recorded_by=request.user,
                proof_reference=request.POST.get('proof_reference', ''),
                notes=request.POST.get('notes', ''),
            )

            messages.success(request, f"Paiement de {payment.total_amount} DA enregistré avec succès pour {teacher.get_full_name()}!")
            return redirect('finance:teacher_payroll_list')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")

    # Récupérer le profil pour la méthode préférée
    profile = getattr(teacher, 'teacher_profile', None)
    preferred_method = profile.preferred_payment_method if profile else 'CASH'

    context = {
        'teacher': teacher,
        'profile': profile,
        'period_start': period_start_str,
        'period_end': period_end_str,
        'amount_due': amount_due,
        'preferred_method': preferred_method,
        'today': today.strftime('%Y-%m-%d'),
    }
    return render(request, 'finance/record_teacher_payment.html', context)


# ========================================================
# SYSTÈME DE PAIE PAR COHORT (NOUVEAU - TDD)
# ========================================================

from academics.models import CourseSession
from .models import TeacherCohortPayment


def teacher_cohort_payroll(request):
    """
    Vue principale : Affiche la paie due pour chaque prof par cohort.
    Calcul automatique basé sur les séances complétées.
    SUPPORTE LES REMPLAÇANTS : Groupe les séances par session.teacher (pas cohort.teacher).
    """
    from academics.models import Cohort
    from collections import defaultdict

    # Filtres - L'utilisateur doit spécifier les dates ou on affiche tout sans filtre de date
    teacher_id = request.GET.get('teacher')
    
    # Si l'utilisateur a fourni des dates, on les utilise
    period_start = request.GET.get('start')
    period_end = request.GET.get('end')
    
    if period_start and period_end:
        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
    else:
        # Pas de filtrage par date par défaut - afficher tous les cohorts avec toutes leurs séances
        period_start = None
        period_end = None

    payroll_data = []

    # Récupérer tous les cohorts
    cohorts = Cohort.objects.select_related('teacher', 'teacher__teacher_profile')

    if teacher_id:
        # Filtrer par prof : inclure les cohorts où il est titulaire OU où il a enseigné des séances
        cohorts_as_teacher = set(cohorts.filter(teacher_id=teacher_id).values_list('id', flat=True))
        sessions_as_sub = CourseSession.objects.filter(teacher_id=teacher_id, status='COMPLETED')
        if period_start and period_end:
            sessions_as_sub = sessions_as_sub.filter(date__gte=period_start, date__lte=period_end)
        cohorts_as_substitute = set(sessions_as_sub.values_list('cohort_id', flat=True))
        
        cohort_ids = cohorts_as_teacher | cohorts_as_substitute
        cohorts = Cohort.objects.filter(id__in=cohort_ids).select_related('teacher', 'teacher__teacher_profile')

    for cohort in cohorts:
        # Récupérer toutes les séances COMPLETED
        sessions_query = CourseSession.objects.filter(
            cohort=cohort,
            status='COMPLETED'
        ).select_related('teacher')
        
        # Appliquer le filtre de date si fourni
        if period_start and period_end:
            sessions_query = sessions_query.filter(
                date__gte=period_start,
                date__lte=period_end
            )

        sessions = sessions_query

        # GROUPER PAR PROFESSEUR (session.teacher)
        sessions_by_teacher = defaultdict(list)
        for session in sessions:
            sessions_by_teacher[session.teacher].append(session)

        # Pour chaque prof ayant enseigné dans ce cohort, créer une ligne
        for teacher, teacher_sessions in sessions_by_teacher.items():
            total_hours = 0
            amount_due = 0

            for session in teacher_sessions:
                hours = float(session.pay_hours)
                rate = session.pay_hourly_rate
                total_hours += hours
                amount_due += hours * rate

            # Récupérer les paiements enregistrés pour ce cohort ET ce prof
            payments_query = TeacherCohortPayment.objects.filter(cohort=cohort, teacher=teacher)
            
            if period_start and period_end:
                payments_query = payments_query.filter(
                    period_start=period_start,
                    period_end=period_end
                )

            payments = payments_query
            total_paid = payments.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
            balance_due = amount_due - float(total_paid)

            if teacher_sessions:  # Afficher seulement si séances
                payroll_data.append({
                    'cohort': cohort,
                    'teacher': teacher,
                    'sessions_count': len(teacher_sessions),
                    'total_hours': round(total_hours, 2),
                    'amount_due': round(amount_due, 2),
                    'total_paid': round(float(total_paid), 2),
                    'balance_due': round(balance_due, 2),
                    'status': 'Soldé' if balance_due <= 0 else f'{balance_due:.0f} DA',
                    'is_paid': balance_due <= 0,
                    'is_substitute': teacher != cohort.teacher,
                })

    teachers = User.objects.filter(is_teacher=True).order_by('first_name')

    context = {
        'payroll_data': payroll_data,
        'teachers': teachers,
        'selected_teacher': teacher_id,
        'period_start': period_start,
        'period_end': period_end,
    }
    return render(request, 'finance/teacher_cohort_payroll.html', context)


def teacher_cohort_payment_detail(request, cohort_id):
    """
    Détail des paiements pour un cohort spécifique.
    Affiche historique et permet d'enregistrer un paiement.
    SUPPORTE LES REMPLAÇANTS : Permet de sélectionner le prof si plusieurs ont enseigné.
    """
    from academics.models import Cohort
    from collections import defaultdict

    cohort = get_object_or_404(Cohort, pk=cohort_id)

    # Récupérer le professeur ciblé (par défaut: titulaire du cohort)
    teacher_id = request.GET.get('teacher')
    if teacher_id:
        teacher = get_object_or_404(User, pk=teacher_id, is_teacher=True)
    else:
        teacher = cohort.teacher

    # Filtres de période - Par défaut: dates du cohort
    # Récupérer les vraies dates des séances du cohort
    sessions_for_cohort = CourseSession.objects.filter(cohort=cohort).order_by('date')
    
    if sessions_for_cohort.exists():
        cohort_start_date = sessions_for_cohort.first().date
        cohort_end_date = sessions_for_cohort.last().date
    else:
        # Si pas de séances, utiliser les dates du cohort
        cohort_start_date = cohort.start_date
        cohort_end_date = cohort.end_date

    # Permettre à l'utilisateur de surcharger les dates
    period_start = request.GET.get('start', '').strip()
    period_end = request.GET.get('end', '').strip()
    
    # Si les dates sont vides, utiliser les dates du cohort
    if not period_start:
        period_start = cohort_start_date.strftime('%Y-%m-%d')
    if not period_end:
        period_end = cohort_end_date.strftime('%Y-%m-%d')

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()

    # Récupérer les séances complétées PAR CE PROF
    sessions = CourseSession.objects.filter(
        cohort=cohort,
        teacher=teacher,
        status='COMPLETED',
        date__gte=period_start,
        date__lte=period_end
    ).order_by('date')

    # Calculer montant dû
    total_hours = 0
    amount_due = 0
    session_details = []

    for session in sessions:
        hours = float(session.pay_hours)
        rate = session.pay_hourly_rate
        pay = hours * rate

        session_details.append({
            'session': session,
            'hours': round(hours, 2),
            'hourly_rate': rate,
            'pay': round(pay, 2),
        })

        total_hours += hours
        amount_due += pay

    # Historique des paiements pour CE PROF
    payment_history = TeacherCohortPayment.objects.filter(
        cohort=cohort,
        teacher=teacher,
        period_start=period_start,
        period_end=period_end
    ).order_by('-payment_date')

    total_paid = payment_history.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    balance_due = amount_due - float(total_paid)
    
    # Liste de tous les profs ayant enseigné dans ce cohort (pour le sélecteur)
    all_teachers_in_cohort = CourseSession.objects.filter(
        cohort=cohort,
        status='COMPLETED'
    ).values_list('teacher', flat=True).distinct()
    teachers_list = User.objects.filter(id__in=all_teachers_in_cohort).order_by('first_name')
    
    today = date.today()

    context = {
        'cohort': cohort,
        'teacher': teacher,
        'period_start': period_start,
        'period_end': period_end,
        'cohort_start_date': cohort_start_date,
        'cohort_end_date': cohort_end_date,
        'session_details': session_details,
        'total_hours': round(total_hours, 2),
        'amount_due': round(amount_due, 2),
        'total_paid': round(float(total_paid), 2),
        'balance_due': round(balance_due, 2),
        'payment_history': payment_history,
        'today': today.strftime('%Y-%m-%d'),
        'preferred_method': teacher.teacher_profile.preferred_payment_method if hasattr(teacher, 'teacher_profile') else 'CASH',
        'teachers_list': teachers_list,
        'is_substitute': teacher != cohort.teacher,
    }
    return render(request, 'finance/teacher_cohort_payment_detail.html', context)


def record_cohort_payment(request, cohort_id):
    """
    Enregistrer un paiement pour un prof pour un cohort spécifique.
    SUPPORTE LES REMPLAÇANTS : Permet de spécifier le prof dans l'URL.
    """
    from academics.models import Cohort

    cohort = get_object_or_404(Cohort, pk=cohort_id)
    
    # Récupérer le professeur ciblé (par défaut: titulaire du cohort)
    teacher_id = request.GET.get('teacher')
    if teacher_id:
        teacher = get_object_or_404(User, pk=teacher_id, is_teacher=True)
    else:
        teacher = cohort.teacher

    if request.method == 'POST':
        try:
            # Handle empty form values safely
            period_start_str = (request.POST.get('period_start') or '').strip()
            period_end_str = (request.POST.get('period_end') or '').strip()
            payment_date_str = (request.POST.get('payment_date') or '').strip()
            amount_due_str = (request.POST.get('amount_due') or '0').strip()
            amount_paid_str = (request.POST.get('amount_paid') or '0').strip()

            # Default period to cohort/session range when missing
            sessions_for_cohort = CourseSession.objects.filter(cohort=cohort).order_by('date')
            if sessions_for_cohort.exists():
                default_start = sessions_for_cohort.first().date
                default_end = sessions_for_cohort.last().date
            else:
                default_start = cohort.start_date
                default_end = cohort.end_date

            if not period_start_str:
                period_start_str = default_start.strftime('%Y-%m-%d')
            if not period_end_str:
                period_end_str = default_end.strftime('%Y-%m-%d')
            if not payment_date_str:
                payment_date_str = date.today().strftime('%Y-%m-%d')

            payment = TeacherCohortPayment.objects.create(
                teacher=teacher,
                cohort=cohort,
                period_start=datetime.strptime(period_start_str, '%Y-%m-%d').date(),
                period_end=datetime.strptime(period_end_str, '%Y-%m-%d').date(),
                amount_due=amount_due_str,
                amount_paid=amount_paid_str,
                payment_date=datetime.strptime(payment_date_str, '%Y-%m-%d').date(),
                payment_method=request.POST.get('payment_method'),
                recorded_by=request.user,
                notes=request.POST.get('notes', ''),
            )

            messages.success(
                request,
                f"Paiement de {payment.amount_paid} DA enregistré pour {teacher.get_full_name()} - {cohort.name}!"
            )
            return redirect('finance:teacher_cohort_payment_detail', cohort_id=cohort.id)

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")

    # Récupérer les infos pour pré-remplir le formulaire
    today = date.today()
    # Determine sensible defaults from cohort/session dates
    sessions_for_cohort = CourseSession.objects.filter(cohort=cohort).order_by('date')
    if sessions_for_cohort.exists():
        default_start = sessions_for_cohort.first().date
        default_end = sessions_for_cohort.last().date
    else:
        default_start = cohort.start_date
        default_end = cohort.end_date

    qs_start = (request.GET.get('start') or '').strip()
    qs_end = (request.GET.get('end') or '').strip()
    period_start_str = qs_start if qs_start else default_start.strftime('%Y-%m-%d')
    period_end_str = qs_end if qs_end else default_end.strftime('%Y-%m-%d')
    amount_due = request.GET.get('amount', '0')

    profile = getattr(teacher, 'teacher_profile', None)
    preferred_method = profile.preferred_payment_method if profile else 'CASH'

    context = {
        'cohort': cohort,
        'teacher': teacher,
        'period_start': period_start_str,
        'period_end': period_end_str,
        'amount_due': amount_due,
        'preferred_method': preferred_method,
        'today': today.strftime('%Y-%m-%d'),
        'is_substitute': teacher != cohort.teacher,
    }
    return render(request, 'finance/record_cohort_payment.html', context)


# ============================================================================
# DASHBOARD PAIEMENTS - Vue synthétique des paiements par étudiant/cohort
# ============================================================================

from django.db.models import Sum, Q, Case, When, DecimalField, F
from django.http import JsonResponse, HttpResponse
from academics.models import Cohort
import csv
from django.utils.timezone import now

@staff_member_required
def payment_status_dashboard(request):
    """
    Dashboard de suivi des paiements.
    Affiche: qui a payé, combien il reste, filtrages par cohort/modality/individual
    """
    
    # Récupérer tous les cohorts pour la liste des filtres
    cohorts = Cohort.objects.all().order_by('name')
    
    # Filtres de la requête
    cohort_id = request.GET.get('cohort', '')
    modality = request.GET.get('modality', '')  # ONLINE ou IN_PERSON
    individual_only = request.GET.get('individual', '')  # '1' pour oui
    status_filter = request.GET.get('status', '')  # IMPAYÉ | PARTIEL | PAYÉ
    search_query = (request.GET.get('q') or '').strip().lower()
    
    # Construire la query de base
    enrollments = Enrollment.objects.filter(is_active=True).select_related(
        'student', 'cohort', 'tariff'
    ).prefetch_related('payments')
    
    # Appliquer les filtres
    if cohort_id:
        enrollments = enrollments.filter(cohort_id=cohort_id)
    
    if modality:
        enrollments = enrollments.filter(cohort__modality=modality)
    
    if individual_only == '1':
        enrollments = enrollments.filter(cohort__is_individual=True)
    
    # Enrichir chaque enrollment avec les stats de paiement
    data = []
    total_tariff = 0
    total_paid = 0
    total_remaining = 0
    
    for enrollment in enrollments:
        total_paid_amount = sum(p.amount for p in enrollment.payments.all())
        remaining = enrollment.tariff.amount - total_paid_amount
        percentage_paid = 0 if enrollment.tariff.amount == 0 else (total_paid_amount / enrollment.tariff.amount) * 100

        status = 'PAYÉ' if remaining == 0 else ('PARTIEL' if total_paid_amount > 0 else 'IMPAYÉ')

        # Filtres rapides applicatifs, sans toucher au calcul métier
        if status_filter and status != status_filter:
            continue

        if search_query:
            full_name = f"{enrollment.student.first_name} {enrollment.student.last_name}".lower()
            student_code = (enrollment.student.student_code or '').lower()
            cohort_name = enrollment.cohort.name.lower()
            if search_query not in full_name and search_query not in student_code and search_query not in cohort_name:
                continue
        
        total_tariff += enrollment.tariff.amount
        total_paid += total_paid_amount
        total_remaining += remaining
        
        pack_info = None
        # Afficher les informations PACK pour toutes les inscriptions en mode PACK
        if enrollment.payment_plan == 'PACK':
            pack_info = {
                'hours_purchased': float(enrollment.hours_purchased),
                'hours_consumed': float(enrollment.hours_consumed),
                'hours_remaining': float(enrollment.hours_remaining),
            }

        data.append({
            'enrollment': enrollment,
            'student_name': f"{enrollment.student.first_name} {enrollment.student.last_name}",
            'student_code': enrollment.student.student_code,
            'cohort_name': enrollment.cohort.name,
            'modality': enrollment.cohort.get_modality_display(),
            'is_individual': enrollment.cohort.is_individual,
            'tariff': enrollment.tariff.amount,
            'paid': total_paid_amount,
            'remaining': remaining,
            'percentage_paid': round(percentage_paid, 1),
            'status': status,
            'pack': pack_info,
        })
    
    # Trier par statut (IMPAYÉ en premier)
    status_order = {'IMPAYÉ': 0, 'PARTIEL': 1, 'PAYÉ': 2}
    data.sort(key=lambda x: (status_order.get(x['status'], 999), x['student_name']))
    
    # Export CSV si demandé
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="paiements.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Code', 'Étudiant', 'Cohort', 'Modalité', 'Tarif', 'Payé', 'Reste', 'Pourcentage', 'Statut'])
        
        for item in data:
            writer.writerow([
                item['student_code'],
                item['student_name'],
                item['cohort_name'],
                item['modality'],
                item['tariff'],
                item['paid'],
                item['remaining'],
                f"{item['percentage_paid']}%",
                item['status'],
            ])
        
        return response
    
    context = {
        'data': data,
        'cohorts': cohorts,
        'selected_cohort': cohort_id,
        'selected_modality': modality,
        'selected_individual': individual_only,
        'selected_status': status_filter,
        'search_query': request.GET.get('q', ''),
        'total_tariff': total_tariff,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'percentage_paid': 0 if total_tariff == 0 else round((total_paid / total_tariff) * 100, 1),
        'count_unpaid': sum(1 for d in data if d['status'] == 'IMPAYÉ'),
        'count_partial': sum(1 for d in data if d['status'] == 'PARTIEL'),
        'count_paid': sum(1 for d in data if d['status'] == 'PAYÉ'),
        # Utile pour afficher une colonne dédiée dans le template
        'has_pack_rows': any(bool(d.get('pack')) for d in data),
    }
    
    return render(request, 'finance/payment_status_dashboard.html', context)