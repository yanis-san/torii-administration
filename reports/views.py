"""
Vues pour la génération de rapports PDF
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.pagesizes import landscape, A4
from datetime import datetime, date, timedelta
import zipfile
import io

from .pdf_utils import PDFReportBase
from .views_zip import generate_all_reports_zip
from students.models import Student, Enrollment, StudentAnnualFee
from academics.models import Cohort, CourseSession, AcademicYear
from finance.models import Payment, TeacherCohortPayment
from cash.models import CashCategory, CashTransaction
from core.models import User
import csv
from django.db.models import Exists, OuterRef


def is_admin(user):
    """Vérifier si l'utilisateur est admin (pas professeur)"""
    return user.is_authenticated and not user.is_teacher


@login_required
@user_passes_test(is_admin)
def reports_menu(request):
    """Menu principal de sélection des rapports"""
    # Compter les étudiants actifs (ceux qui ont au moins une inscription active)
    active_student_ids = Enrollment.objects.filter(is_active=True).values_list('student_id', flat=True).distinct()
    
    context = {
        'total_students': active_student_ids.count(),
        'total_cohorts': Cohort.objects.count(),
        'total_sessions': CourseSession.objects.count(),
        'total_teachers': User.objects.filter(is_teacher=True).count(),
    }
    return render(request, 'reports/menu.html', context)


@login_required
@user_passes_test(is_admin)
def export_retained_students_csv(request):
    """Exporter en CSV les étudiants qui sont restés (2+ inscriptions au total)"""
    response = HttpResponse(content_type='text/csv')
    filename = f"etudiants_retenus_{datetime.now().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Nom', 'Prénom', 'Code', 'Email', 'Téléphone', 'Nb Inscriptions', '1ère inscription', 'Dernière inscription'])

    # Étudiants avec 2+ inscriptions
    students = Student.objects.annotate(enroll_count=Count('enrollments')).filter(enroll_count__gte=2)
    for s in students:
        enrolls = s.enrollments.order_by('date').select_related('cohort')
        first_date = enrolls.first().date if enrolls.exists() else None
        last_date = enrolls.last().date if enrolls.exists() else None
        writer.writerow([
            s.last_name,
            s.first_name,
            s.student_code,
            s.email or '',
            s.phone,
            enrolls.count(),
            first_date.strftime('%d/%m/%Y') if first_date else '',
            last_date.strftime('%d/%m/%Y') if last_date else '',
        ])

    return response


@login_required
@user_passes_test(is_admin)
def report_all_students(request):
    """Rapport PDF: Liste de tous les étudiants actifs"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="etudiants_complet_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    # Créer le PDF en paysage
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    # En-tête
    pdf.add_header(elements, 
                   "LISTE COMPLÈTE DES ÉTUDIANTS",
                   "Tous les étudiants actifs de l'institut")
    
    # Statistiques - étudiants avec au moins une inscription active
    active_student_ids = Enrollment.objects.filter(is_active=True).values_list('student_id', flat=True).distinct()
    total_students = active_student_ids.count()
    
    pdf.add_info_section(elements, {
        'Total étudiants actifs': total_students,
        'Date du rapport': datetime.now().strftime('%d/%m/%Y'),
    })
    
    elements.append(Spacer(1, 5))
    
    # Tableau des étudiants
    students = Student.objects.filter(id__in=active_student_ids).order_by('last_name', 'first_name')
    
    if students.exists():
        # Ajouter statut des frais d'inscription pour l'année académique active
        current_year = AcademicYear.get_current()
        data = [['Nom Complet', 'Email', 'Téléphone', 'Inscriptions', 'Frais Inscription']]
        
        for student in students:
            enrollments_count = student.enrollments.filter(is_active=True).count()
            fee_status = 'Oui' if student.has_paid_registration_fee(current_year) else 'Non'
            data.append([
                f"{student.last_name} {student.first_name}",
                student.email or '-',
                student.phone or '-',
                str(enrollments_count),
                fee_status
            ]);
        
        # Colonnes 0 (Nom) et 1 (Email) avec retour à la ligne
        table = pdf.create_data_table(data, col_widths=[5*cm, 5*cm, 3.0*cm, 2.0*cm, 3.0*cm], wrap_columns=[0, 1])
        elements.append(table)
    else:
        elements.append(Paragraph("Aucun étudiant actif trouvé.", pdf.styles['Normal']))
    
    # Construire le PDF
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def report_cohort_students(request, cohort_id):
    """Rapport PDF: Liste des étudiants d'un cohort spécifique"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="etudiants_{cohort.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    # En-tête
    pdf.add_header(elements,
                   f"LISTE DES ÉTUDIANTS",
                   cohort.name)
    
    # Informations du cohort
    pdf.add_info_section(elements, {
        'Groupe': cohort.name,
        'Matière': cohort.subject.name,
        'Niveau': cohort.level.name,
        'Professeur': cohort.teacher.get_full_name(),
        'Période': f"{cohort.start_date.strftime('%d/%m/%Y')} - {cohort.end_date.strftime('%d/%m/%Y')}",
        'Prix standard': f"{cohort.standard_price} DA",
    })
    
    elements.append(Spacer(1, 5))
    
    # Tableau des étudiants
    enrollments = cohort.enrollments.filter(is_active=True).select_related('student', 'tariff')
    
    if enrollments.exists():
        data = [['Contrat', 'Date', 'Nom Complet', 'Email', 'Téléphone', 'Plan', 'Pack (h)', 'Frais Inscr.', 'Prix', 'Payé', 'Reste']]
        
        for enrollment in enrollments:
            student = enrollment.student
            balance = enrollment.balance_due
            total_paid = sum(p.amount for p in enrollment.payments.all())
            fee_status = 'Oui' if student.has_paid_registration_fee(cohort.academic_year) else 'Non'
            plan_label = {'FULL': 'Totalité', 'MONTHLY': 'Mensuel', 'PACK': 'Pack'}.get(enrollment.payment_plan, enrollment.payment_plan)
            pack_info = '-'
            if enrollment.payment_plan == 'PACK':
                pack_info = f"{enrollment.hours_remaining:.1f}/{enrollment.hours_purchased:.1f}"
            data.append([
                enrollment.contract_code or '-',
                enrollment.date.strftime('%d/%m/%Y') if enrollment.date else '-',
                f"{student.last_name} {student.first_name}",
                student.email or '-',
                student.phone or '-',
                plan_label,
                pack_info,
                fee_status,
                f"{enrollment.tariff.amount} DA",
                f"{total_paid} DA",
                f"{balance} DA"
            ])
        
        # Largeurs paysage: ~25cm disponibles
        table = pdf.create_data_table(data, col_widths=[2.8*cm, 2.0*cm, 4.5*cm, 3.5*cm, 2.8*cm, 2.0*cm, 1.8*cm, 1.8*cm, 2.0*cm, 2.0*cm, 2.0*cm], wrap_columns=[0, 2, 3])
        elements.append(table)
    else:
        elements.append(Paragraph("Aucun étudiant inscrit dans ce groupe.", pdf.styles['Normal']))
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def report_cohort_sessions(request, cohort_id):
    """Rapport PDF: Détail des séances d'un cohort avec présences et remplacements"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="seances_{cohort.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    # En-tête
    pdf.add_header(elements,
                   f"RAPPORT DES SÉANCES",
                   cohort.name)
    
    # Informations du cohort
    sessions = cohort.sessions.all().order_by('date', 'start_time')
    completed_count = sessions.filter(status='COMPLETED').count()
    postponed_count = sessions.filter(status='POSTPONED').count()
    
    pdf.add_info_section(elements, {
        'Groupe': cohort.name,
        'Professeur titulaire': cohort.teacher.get_full_name(),
        'Total séances': sessions.count(),
        'Séances complétées': completed_count,
        'Séances reportées': postponed_count,
    })
    
    elements.append(Spacer(1, 5))
    
    # Tableau des séances
    if sessions.exists():
        data = [['Date', 'Horaire', 'Professeur', 'Statut', 'Note']]
        
        for session in sessions:
            # Déterminer si remplaçant
            teacher_name = session.teacher.get_full_name()
            if session.teacher.id != cohort.teacher.id:
                teacher_name += " (Remplaçant)"
            
            # Statut
            status_map = {
                'SCHEDULED': 'Prévu',
                'COMPLETED': 'Terminé',
                'CANCELLED': 'Annulé',
                'POSTPONED': 'Reporté'
            }
            status = status_map.get(session.status, session.status)
            
            # Note (extraire les changements de prof)
            note = ""
            if session.note and "Changement prof" in session.note:
                note = "Prof changé"
            elif session.note and "Reporté" in session.note:
                note = "Reporté"
            
            data.append([
                session.date.strftime('%d/%m/%Y'),
                f"{session.start_time.strftime('%H:%M')}-{session.end_time.strftime('%H:%M')}",
                teacher_name,
                status,
                note
            ])
        
        # Colonnes 2 (Professeur) et 4 (Note) avec retour à la ligne
        table = pdf.create_data_table(data, col_widths=[3*cm, 3*cm, 5*cm, 2.5*cm, 3.5*cm], wrap_columns=[2, 4])
        elements.append(table)
    else:
        elements.append(Paragraph("Aucune séance programmée.", pdf.styles['Normal']))
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def report_unpaid_annual_fees_pdf(request):
    """PDF: Étudiants inscrits sur l'année (optionnel subject/cohort) qui n'ont pas payé les frais annuels."""
    year_param = request.GET.get('year')
    subject_id = request.GET.get('subject')
    cohort_id = request.GET.get('cohort')

    year_obj = None
    if year_param:
        try:
            year_obj = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            year_obj = AcademicYear.objects.filter(label=year_param).first()
    if not year_obj:
        year_obj = AcademicYear.get_current()

    # Base enrollments for the selected year
    enroll_qs = Enrollment.objects.select_related('student', 'cohort__subject', 'cohort__academic_year')
    if year_obj:
        enroll_qs = enroll_qs.filter(cohort__academic_year=year_obj)
    if subject_id:
        try:
            enroll_qs = enroll_qs.filter(cohort__subject_id=int(subject_id))
        except Exception:
            pass
    if cohort_id:
        try:
            enroll_qs = enroll_qs.filter(cohort_id=int(cohort_id))
        except Exception:
            pass

    student_ids = enroll_qs.filter(is_active=True).values_list('student_id', flat=True).distinct()

    # Students without a PAID fee record for the year
    paid_fee = StudentAnnualFee.objects.filter(
        student_id=OuterRef('pk'),
        academic_year=year_obj,
        is_paid=True,
    )
    students_qs = Student.objects.filter(id__in=student_ids).annotate(fee_paid=Exists(paid_fee)).filter(fee_paid=False)

    # Build PDF en paysage
    response = HttpResponse(content_type='application/pdf')
    title_suffix = year_obj.label if year_obj else 'Annee_active'
    response['Content-Disposition'] = f'attachment; filename="frais_inscription_impayes_{title_suffix}_{datetime.now().strftime("%Y%m%d")}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()

    subtitle = f"Année académique: {year_obj.label}" if year_obj else "Année académique active"
    pdf.add_header(elements, "FRAIS D'INSCRIPTION - NON PAYÉS", subtitle)

    pdf.add_info_section(elements, {
        'Étudiants concernés': students_qs.count(),
        'Date du rapport': datetime.now().strftime('%d/%m/%Y'),
    })

    elements.append(Spacer(1, 6))

    data = [['Nom', 'Prénom', 'Code', 'Email', 'Téléphone', 'Nb Inscriptions (année)']]
    # Pre-calculate enrollment counts per student for the year
    enroll_counts = {sid: cnt for sid, cnt in enroll_qs.values_list('student_id').annotate(cnt=Count('id'))}
    for s in students_qs.order_by('last_name', 'first_name'):
        data.append([
            s.last_name,
            s.first_name,
            s.student_code or '-',
            s.email or '-',
            s.phone or '-',
            str(enroll_counts.get(s.id, 0)),
        ])

    if len(data) == 1:
        elements.append(Paragraph("Aucun étudiant en défaut pour cette période.", pdf.styles['Normal']))
    else:
        table = pdf.create_data_table(data, col_widths=[3.5*cm, 3.5*cm, 3*cm, 5*cm, 3.5*cm, 3*cm], wrap_columns=[0, 3])
        elements.append(table)

    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def export_unpaid_annual_fees_csv(request):
    """CSV: Étudiants non payés des frais d'inscription pour l'année (ou active)."""
    year_param = request.GET.get('year')
    subject_id = request.GET.get('subject')
    cohort_id = request.GET.get('cohort')

    year_obj = None
    if year_param:
        try:
            year_obj = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            year_obj = AcademicYear.objects.filter(label=year_param).first()
    if not year_obj:
        year_obj = AcademicYear.get_current()

    enroll_qs = Enrollment.objects.select_related('student', 'cohort__subject', 'cohort__academic_year')
    if year_obj:
        enroll_qs = enroll_qs.filter(cohort__academic_year=year_obj)
    if subject_id:
        try:
            enroll_qs = enroll_qs.filter(cohort__subject_id=int(subject_id))
        except Exception:
            pass
    if cohort_id:
        try:
            enroll_qs = enroll_qs.filter(cohort_id=int(cohort_id))
        except Exception:
            pass

    student_ids = enroll_qs.filter(is_active=True).values_list('student_id', flat=True).distinct()
    paid_fee = StudentAnnualFee.objects.filter(
        student_id=OuterRef('pk'), academic_year=year_obj, is_paid=True
    )
    students_qs = Student.objects.filter(id__in=student_ids).annotate(fee_paid=Exists(paid_fee)).filter(fee_paid=False)

    response = HttpResponse(content_type='text/csv')
    title_suffix = year_obj.label if year_obj else 'Annee_active'
    response['Content-Disposition'] = f'attachment; filename="frais_inscription_impayes_{title_suffix}_{datetime.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Année', year_obj.label if year_obj else 'Active'])
    writer.writerow([])
    writer.writerow(['Nom', 'Prénom', 'Code', 'Email', 'Téléphone', 'Nb Inscriptions (année)'])

    enroll_counts = {sid: cnt for sid, cnt in enroll_qs.values_list('student_id').annotate(cnt=Count('id'))}
    for s in students_qs.order_by('last_name', 'first_name'):
        writer.writerow([
            s.last_name,
            s.first_name,
            s.student_code or '',
            s.email or '',
            s.phone or '',
            enroll_counts.get(s.id, 0),
        ])

    return response


@login_required
@user_passes_test(is_admin)
def report_payments_monthly(request):
    """Rapport PDF: Paiements étudiants mensuels"""
    # Récupérer le mois depuis GET ou utiliser le mois actuel
    month = request.GET.get('month', datetime.now().month)
    year = request.GET.get('year', datetime.now().year)
    
    try:
        month = int(month)
        year = int(year)
    except:
        month = datetime.now().month
        year = datetime.now().year
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="paiements_{year}_{month:02d}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    # En-tête
    month_names = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                   'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    pdf.add_header(elements,
                   f"RAPPORT DES PAIEMENTS",
                   f"{month_names[month]} {year}")
    
    # Récupérer les paiements du mois
    payments = Payment.objects.filter(
        date__month=month,
        date__year=year
    ).select_related('enrollment__student', 'enrollment__cohort', 'recorded_by').order_by('date')
    
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    pdf.add_info_section(elements, {
        'Période': f"{month_names[month]} {year}",
        'Nombre de paiements': payments.count(),
        'Montant total': f"{total_amount:,.0f} DA",
    })
    
    elements.append(Spacer(1, 5))
    
    # Tableau des paiements
    if payments.exists():
        data = [['Date', 'Étudiant', 'Groupe', 'Montant', 'Enregistré par']]
        
        for payment in payments:
            data.append([
                payment.date.strftime('%d/%m/%Y'),
                f"{payment.enrollment.student.last_name} {payment.enrollment.student.first_name}",
                payment.enrollment.cohort.name,
                f"{payment.amount:,.0f} DA",
                payment.recorded_by.get_full_name() if payment.recorded_by else '-'
            ])
        
        # Colonnes 1 (Étudiant), 2 (Groupe) et 4 (Enregistré par) avec retour à la ligne
        table = pdf.create_data_table(data, col_widths=[2.5*cm, 4*cm, 4.5*cm, 2.5*cm, 3.5*cm], wrap_columns=[1, 2, 4])
        elements.append(table)
    else:
        elements.append(Paragraph("Aucun paiement enregistré pour cette période.", pdf.styles['Normal']))
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def report_teacher_payroll(request):
    """Rapport PDF: Paie des professeurs"""
    # Récupérer la période depuis GET
    period_start = request.GET.get('start')
    period_end = request.GET.get('end')
    
    if period_start and period_end:
        try:
            period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
        except:
            period_start = None
            period_end = None
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"paie_professeurs_{datetime.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    # En-tête
    subtitle = "Toutes les périodes"
    if period_start and period_end:
        subtitle = f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}"
    
    pdf.add_header(elements, "RAPPORT DE PAIE PROFESSEURS", subtitle)
    
    # Récupérer les données de paie
    from collections import defaultdict
    from academics.models import CourseSession
    
    cohorts = Cohort.objects.select_related('teacher').all()
    payroll_data = []
    
    for cohort in cohorts:
        sessions_query = CourseSession.objects.filter(cohort=cohort, status='COMPLETED')
        
        if period_start and period_end:
            sessions_query = sessions_query.filter(date__gte=period_start, date__lte=period_end)
        
        sessions = sessions_query.select_related('teacher')
        sessions_by_teacher = defaultdict(list)
        
        for session in sessions:
            sessions_by_teacher[session.teacher].append(session)
        
        for teacher, teacher_sessions in sessions_by_teacher.items():
            total_hours = 0
            for session in teacher_sessions:
                # Utilise duration_hours qui prend en compte l'override
                total_hours += float(session.duration_hours)
            
            amount_due = total_hours * cohort.teacher_hourly_rate
            
            if teacher_sessions:
                payroll_data.append({
                    'teacher': teacher,
                    'cohort': cohort,
                    'sessions_count': len(teacher_sessions),
                    'total_hours': round(total_hours, 2),
                    'amount_due': round(amount_due, 2),
                    'is_substitute': teacher.id != cohort.teacher.id
                })
    
    total_to_pay = sum(item['amount_due'] for item in payroll_data)
    
    pdf.add_info_section(elements, {
        'Nombre de professeurs': len(set(item['teacher'] for item in payroll_data)),
        'Total à payer': f"{total_to_pay:,.0f} DA",
    })
    
    elements.append(Spacer(1, 5))
    
    # Tableau de paie
    if payroll_data:
        data = [['Professeur', 'Groupe', 'Séances', 'Heures', 'Montant Dû']]
        
        for item in payroll_data:
            teacher_name = item['teacher'].get_full_name()
            if item['is_substitute']:
                teacher_name += " (Remplaçant)"
            
            data.append([
                teacher_name,
                item['cohort'].name,
                str(item['sessions_count']),
                f"{item['total_hours']}h",
                f"{item['amount_due']:,.0f} DA"
            ])
        
        # Colonnes 0 (Professeur) et 1 (Groupe) avec retour à la ligne
        table = pdf.create_data_table(data, col_widths=[4.5*cm, 5*cm, 2*cm, 2*cm, 3.5*cm], wrap_columns=[0, 1])
        elements.append(table)
    else:
        elements.append(Paragraph("Aucune donnée de paie disponible.", pdf.styles['Normal']))
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def annual_reports_page(request):
    """Page de sélection de l'année académique et actions d'export"""
    years = AcademicYear.objects.order_by('-start_date')
    selected = request.GET.get('year')
    selected_year = None
    if selected:
        try:
            # Essayer par id puis par label
            selected_year = AcademicYear.objects.get(id=int(selected))
        except Exception:
            selected_year = AcademicYear.objects.filter(label=selected).first()

    modality_filter = request.GET.get('modality', '')
    individual_filter = request.GET.get('individual', '')

    context = {
        'years': years,
        'selected_year': selected_year,
        'selected_year_value': (selected_year.id if selected_year else ''),
        'modality_filter': modality_filter,
        'individual_filter': individual_filter,
    }
    return render(request, 'reports/annual.html', context)


@login_required
@user_passes_test(is_admin)
def report_enrollments_by_academic_year(request):
    """PDF: Étudiants inscrits par Année Académique, groupés par matière puis cohort"""
    year_param = request.GET.get('year')  # id ou label; vide => toutes années
    modality_filter = request.GET.get('modality')  # 'ONLINE' | 'IN_PERSON' | ''
    individual_filter = request.GET.get('individual')  # '1' | '0' | ''
    
    year_obj = None
    if year_param:
        try:
            year_obj = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            year_obj = AcademicYear.objects.filter(label=year_param).first()

    response = HttpResponse(content_type='application/pdf')
    title_suffix = year_obj.label if year_obj else 'Toutes_annees'
    response['Content-Disposition'] = f'attachment; filename="inscriptions_{title_suffix}_{datetime.now().strftime("%Y%m%d")}.pdf"'

    # Paysage pour plus d'espace
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()

    subtitle = f"Année académique: {year_obj.label}" if year_obj else "Toutes les années académiques"
    pdf.add_header(elements, "INSCRIPTIONS PAR ANNÉE ACADÉMIQUE", subtitle)

    # Récupérer les cohortes pour l'année avec filtres modality/individual
    cohorts_qs = Cohort.objects.select_related('subject', 'level', 'academic_year', 'teacher')
    if year_obj:
        cohorts_qs = cohorts_qs.filter(academic_year=year_obj)
    if modality_filter in ['ONLINE', 'IN_PERSON']:
        cohorts_qs = cohorts_qs.filter(modality=modality_filter)
    if individual_filter == '1':
        cohorts_qs = cohorts_qs.filter(is_individual=True)
    elif individual_filter == '0':
        cohorts_qs = cohorts_qs.filter(is_individual=False)

    from collections import defaultdict
    by_subject = defaultdict(list)
    for c in cohorts_qs.order_by('subject__name', 'name'):
        by_subject[c.subject.name].append(c)

    # Résumé global avant les détails
    total_cohorts = 0
    total_enrollments_all = 0
    total_tariff_sum_all = 0
    total_paid_sum_all = 0
    fully_paid_count = 0
    with_balance_count = 0

    for subject_name in by_subject.keys():
        for cohort in by_subject[subject_name]:
            enrollments = cohort.enrollments.select_related('student', 'tariff').all()
            if not enrollments.exists():
                continue
            total_cohorts += 1
            total_enrollments_all += enrollments.count()
            cohort_tariff = sum((e.tariff.amount if e.tariff else 0) for e in enrollments)
            cohort_paid = sum(sum(p.amount for p in e.payments.all()) for e in enrollments)
            total_tariff_sum_all += cohort_tariff
            total_paid_sum_all += cohort_paid
            for e in enrollments:
                paid = sum(p.amount for p in e.payments.all())
                if (e.tariff.amount if e.tariff else 0) - paid <= 0:
                    fully_paid_count += 1
                else:
                    with_balance_count += 1

    pdf.add_info_section(elements, {
        'Cohorts avec inscriptions': total_cohorts,
        'Total inscriptions': total_enrollments_all,
        'Total facturé (toutes)': f"{total_tariff_sum_all:,.0f} DA",
        'Total payé (toutes)': f"{total_paid_sum_all:,.0f} DA",
        'Reste global': f"{(total_tariff_sum_all - total_paid_sum_all):,.0f} DA",
        'Soldés': fully_paid_count,
        'Avec reste': with_balance_count,
    })

    total_enrollments = 0
    for subject_name in sorted(by_subject.keys()):
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(subject_name.upper(), pdf.styles['CustomSection']))

        for cohort in by_subject[subject_name]:
            # Inscriptions de ce cohort
            enrollments = cohort.enrollments.select_related('student', 'tariff').all()
            if not enrollments.exists():
                continue
            total_enrollments += enrollments.count()

            # Infos du cohort
            # Totaux financiers
            total_tariff_sum = sum((e.tariff.amount if e.tariff else 0) for e in enrollments)
            total_paid_sum = sum(sum(p.amount for p in e.payments.all()) for e in enrollments)
            balance_sum = total_tariff_sum - total_paid_sum
            
            # Modalité et individual
            modality_label = "En ligne" if cohort.modality == "ONLINE" else "Présentiel"
            individual_label = "Oui" if cohort.is_individual else "Non"

            pdf.add_info_section(elements, {
                'Groupe': cohort.name,
                'Niveau': cohort.level.name,
                'Prof': cohort.teacher.get_full_name(),
                'Modalité': modality_label,
                'Individuel': individual_label,
                'Période': f"{cohort.start_date.strftime('%d/%m/%Y')} - {cohort.end_date.strftime('%d/%m/%Y')}",
                'Inscrits': enrollments.count(),
                'Total facturé': f"{total_tariff_sum:,.0f} DA",
                'Total payé': f"{total_paid_sum:,.0f} DA",
                'Reste global': f"{balance_sum:,.0f} DA",
            })

            # Tableau étudiants (avec colonnes Actif + Frais Inscription + Code Contrat + Date Inscription + Plan + Pack)
            data = [['Contrat', 'Date', 'Étudiant', 'Téléphone', 'Email', 'Code Étudiant', 'Actif', 'Frais Inscr.', 'Plan', 'Pack (h)', 'Prix', 'Payé', 'Reste']]
            for e in enrollments:
                s = e.student
                total_paid = sum(p.amount for p in e.payments.all())
                balance = (e.tariff.amount if e.tariff else 0) - total_paid
                plan_label = {'FULL': 'Totalité', 'MONTHLY': 'Mensuel', 'PACK': 'Pack'}.get(e.payment_plan, e.payment_plan)
                pack_info = '-'
                if e.payment_plan == 'PACK':
                    pack_info = f"{e.hours_remaining:.1f}/{e.hours_purchased:.1f}"
                data.append([
                    getattr(e, 'contract_code', '-') or '-',
                    (e.date.strftime('%d/%m/%Y') if getattr(e, 'date', None) else '-'),
                    f"{s.last_name} {s.first_name}",
                    s.phone or '-',
                    s.email or '-',
                    s.student_code or '-',
                    ('Oui' if e.is_active else 'Non'),
                    ('Oui' if s.has_paid_registration_fee(year_obj) else 'Non'),
                    plan_label,
                    pack_info,
                    f"{e.tariff.amount if e.tariff else 0:,.0f} DA",
                    f"{total_paid:,.0f} DA",
                    f"{balance:,.0f} DA",
                ])

            # Largeurs adaptées paysage pour 13 colonnes (~25 cm disponibles)
            table = pdf.create_data_table(
                data,
                col_widths=[2.8*cm, 1.8*cm, 4.0*cm, 2.5*cm, 3.5*cm, 2.0*cm, 1.3*cm, 1.5*cm, 1.8*cm, 1.6*cm, 1.8*cm, 1.8*cm, 1.8*cm],
                wrap_columns=[2, 4],
                compact=False
            )
            elements.append(table)
            elements.append(Spacer(1, 6))

    if total_enrollments == 0:
        elements.append(Paragraph("Aucune inscription trouvée pour cette période.", pdf.styles['Normal']))

    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def export_enrollments_by_academic_year_csv(request):
    """CSV: Étudiants inscrits filtrés par année académique (Excel)"""
    year_param = request.GET.get('year')
    modality_filter = request.GET.get('modality')
    individual_filter = request.GET.get('individual')
    
    year_obj = None
    if year_param:
        try:
            year_obj = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            year_obj = AcademicYear.objects.filter(label=year_param).first()

    response = HttpResponse(content_type='text/csv')
    title_suffix = year_obj.label if year_obj else 'Toutes_annees'
    response['Content-Disposition'] = f'attachment; filename="inscriptions_{title_suffix}_{datetime.now().strftime("%Y%m%d")}.csv"'

    import csv
    writer = csv.writer(response)
    writer.writerow(['Année', year_obj.label if year_obj else 'Toutes'])
    writer.writerow([])
    writer.writerow(['Sujet', 'Groupe', 'Modalité', 'Individuel', 'Contrat', 'Date', 'Étudiant', 'Téléphone', 'Email', 'Code Étudiant', 'Actif', 'Frais Inscription', 'Plan', 'Pack (h)', 'Prix', 'Payé', 'Reste'])

    cohorts_qs = Cohort.objects.select_related('subject', 'level', 'academic_year', 'teacher')
    if year_obj:
        cohorts_qs = cohorts_qs.filter(academic_year=year_obj)
    if modality_filter in ['ONLINE', 'IN_PERSON']:
        cohorts_qs = cohorts_qs.filter(modality=modality_filter)
    if individual_filter == '1':
        cohorts_qs = cohorts_qs.filter(is_individual=True)
    elif individual_filter == '0':
        cohorts_qs = cohorts_qs.filter(is_individual=False)

    for cohort in cohorts_qs.order_by('subject__name', 'name'):
        enrollments = cohort.enrollments.select_related('student', 'tariff').all()
        modality_label = "En ligne" if cohort.modality == "ONLINE" else "Présentiel"
        individual_label = "Oui" if cohort.is_individual else "Non"
        for e in enrollments:
            s = e.student
            total_paid = sum(p.amount for p in e.payments.all())
            balance = (e.tariff.amount if e.tariff else 0) - total_paid
            plan_label = {'FULL': 'Totalité', 'MONTHLY': 'Mensuel', 'PACK': 'Pack'}.get(e.payment_plan, e.payment_plan)
            pack_info = ''
            if e.payment_plan == 'PACK':
                pack_info = f"{e.hours_remaining:.1f}/{e.hours_purchased:.1f}"
            writer.writerow([
                cohort.subject.name,
                cohort.name,
                modality_label,
                individual_label,
                getattr(e, 'contract_code', '') or '',
                (e.date.strftime('%d/%m/%Y') if getattr(e, 'date', None) else ''),
                f"{s.last_name} {s.first_name}",
                s.phone or '',
                s.email or '',
                s.student_code or '',
                ('Oui' if e.is_active else 'Non'),
                ('Oui' if s.has_paid_registration_fee(year_obj) else 'Non'),
                plan_label,
                pack_info,
                e.tariff.amount if e.tariff else 0,
                total_paid,
                balance
            ])

    return response


@login_required
@user_passes_test(is_admin)
def report_enrollments_by_academic_year_zip(request):
    """ZIP: Un PDF par cohort pour l'année académique sélectionnée"""
    year_param = request.GET.get('year')
    modality_filter = request.GET.get('modality')
    individual_filter = request.GET.get('individual')
    
    year_obj = None
    if year_param:
        try:
            year_obj = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            year_obj = AcademicYear.objects.filter(label=year_param).first()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        cohorts_qs = Cohort.objects.select_related('subject', 'level', 'academic_year', 'teacher')
        if year_obj:
            cohorts_qs = cohorts_qs.filter(academic_year=year_obj)
        if modality_filter in ['ONLINE', 'IN_PERSON']:
            cohorts_qs = cohorts_qs.filter(modality=modality_filter)
        if individual_filter == '1':
            cohorts_qs = cohorts_qs.filter(is_individual=True)
        elif individual_filter == '0':
            cohorts_qs = cohorts_qs.filter(is_individual=False)

        for cohort in cohorts_qs.order_by('subject__name', 'name'):
            enrollments = cohort.enrollments.select_related('student', 'tariff').all()
            if not enrollments.exists():
                continue

            # Construire un PDF individuel en mémoire
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4),
                                    leftMargin=2*cm, rightMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            pdf = PDFReportBase()
            pdf.add_header(elements, f"INSCRIPTIONS - {cohort.name}", f"{cohort.subject.name} - {cohort.academic_year.label}")
            # Totaux financiers
            total_tariff_sum = sum((e.tariff.amount if e.tariff else 0) for e in enrollments)
            total_paid_sum = sum(sum(p.amount for p in e.payments.all()) for e in enrollments)
            balance_sum = total_tariff_sum - total_paid_sum
            
            modality_label = "En ligne" if cohort.modality == "ONLINE" else "Présentiel"
            individual_label = "Oui" if cohort.is_individual else "Non"
            
            pdf.add_info_section(elements, {
                'Niveau': cohort.level.name,
                'Prof': cohort.teacher.get_full_name(),
                'Modalité': modality_label,
                'Individuel': individual_label,
                'Période': f"{cohort.start_date.strftime('%d/%m/%Y')} - {cohort.end_date.strftime('%d/%m/%Y')}",
                'Inscrits': enrollments.count(),
                'Total facturé': f"{total_tariff_sum:,.0f} DA",
                'Total payé': f"{total_paid_sum:,.0f} DA",
                'Reste global': f"{balance_sum:,.0f} DA",
            })

            data = [['Contrat', 'Date', 'Étudiant', 'Téléphone', 'Email', 'Code Étudiant', 'Actif', 'Frais Inscr.', 'Plan', 'Pack (h)', 'Prix', 'Payé', 'Reste']]
            for e in enrollments:
                s = e.student
                total_paid = sum(p.amount for p in e.payments.all())
                balance = (e.tariff.amount if e.tariff else 0) - total_paid
                plan_label = {'FULL': 'Totalité', 'MONTHLY': 'Mensuel', 'PACK': 'Pack'}.get(e.payment_plan, e.payment_plan)
                pack_info = '-'
                if e.payment_plan == 'PACK':
                    pack_info = f"{e.hours_remaining:.1f}/{e.hours_purchased:.1f}"
                data.append([
                    getattr(e, 'contract_code', '-') or '-',
                    (e.date.strftime('%d/%m/%Y') if getattr(e, 'date', None) else '-'),
                    f"{s.last_name} {s.first_name}",
                    s.phone or '-',
                    s.email or '-',
                    s.student_code or '-',
                    ('Oui' if e.is_active else 'Non'),
                    ('Oui' if s.has_paid_registration_fee(year_obj) else 'Non'),
                    plan_label,
                    pack_info,
                    f"{e.tariff.amount if e.tariff else 0:,.0f} DA",
                    f"{total_paid:,.0f} DA",
                    f"{balance:,.0f} DA",
                ])

            table = pdf.create_data_table(
                data,
                col_widths=[2.8*cm, 1.8*cm, 4.0*cm, 2.5*cm, 3.5*cm, 2.0*cm, 1.3*cm, 1.5*cm, 1.8*cm, 1.6*cm, 1.8*cm, 1.8*cm, 1.8*cm],
                wrap_columns=[2, 4],
                compact=False
            )
            elements.append(table)

            doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()

            fname = f"{cohort.subject.name}_{cohort.name}_{cohort.academic_year.label}.pdf".replace(' ', '_')
            zf.writestr(fname, pdf_bytes)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    zname = f"inscriptions_{(year_obj.label if year_obj else 'Toutes_annees')}_{datetime.now().strftime('%Y%m%d')}.zip"
    response['Content-Disposition'] = f'attachment; filename="{zname.replace(' ', '_')}"'
    return response


@login_required
@user_passes_test(is_admin)
def cash_reports_page(request):
    """Page avec onglets Alpine.js pour rapports de caisse"""
    # Données de base
    categories = CashCategory.objects.all().order_by('-is_total', 'name')
    total_cash = sum(cat.current_amount for cat in categories if not cat.is_total)
    # Filtres date pour transactions
    start = request.GET.get('start')
    end = request.GET.get('end')
    category_param = request.GET.get('category')  # id or name
    start_date = None
    end_date = None
    if start:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        except Exception:
            start_date = None
    if end:
        try:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except Exception:
            end_date = None
    tx_qs = CashTransaction.objects.select_related('category', 'created_by').order_by('-created_at')
    # Filtre catégorie si fourni
    selected_category = None
    if category_param:
        try:
            selected_category = CashCategory.objects.get(id=int(category_param))
            tx_qs = tx_qs.filter(category=selected_category)
        except Exception:
            try:
                selected_category = CashCategory.objects.get(name=category_param)
                tx_qs = tx_qs.filter(category=selected_category)
            except Exception:
                selected_category = None
    if start_date:
        tx_qs = tx_qs.filter(created_at__date__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__date__lte=end_date)
    context = {
        'categories': categories,
        'total_cash': total_cash,
        'transactions': tx_qs[:200],  # limiter affichage
        'start': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end': end_date.strftime('%Y-%m-%d') if end_date else '',
        'selected_category': selected_category,
        'selected_category_id': selected_category.id if selected_category else '',
    }
    return render(request, 'reports/cash_reports.html', context)


@login_required
@user_passes_test(is_admin)
def export_cash_csv(request):
    """Exporter la caisse au format CSV (Excel compatible)"""
    # Filtres
    start = request.GET.get('start')
    end = request.GET.get('end')
    category_param = request.GET.get('category')
    start_date = None
    end_date = None
    if start:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        except Exception:
            start_date = None
    if end:
        try:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except Exception:
            end_date = None

    response = HttpResponse(content_type='text/csv')
    # Option categorie
    category_filter = None
    if category_param:
        try:
            category_filter = CashCategory.objects.get(id=int(category_param))
        except Exception:
            try:
                category_filter = CashCategory.objects.get(name=category_param)
            except Exception:
                category_filter = None
    suffix = f"_{category_filter.name}" if category_filter else ''
    filename = f"cash{suffix}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # Feuille 1: Catégories (CSV ne gère pas onglets, mais section header)
    writer.writerow(['CATEGORIES'])
    writer.writerow(['Nom', 'Montant actuel (DA)', 'Dernier reset', 'Est TOTAL'])
    cats_qs = CashCategory.objects.all().order_by('-is_total', 'name')
    if category_filter:
        cats_qs = cats_qs.filter(id=category_filter.id)
    for cat in cats_qs:
        writer.writerow([
            cat.name,
            cat.current_amount,
            cat.last_reset.strftime('%d/%m/%Y %H:%M') if cat.last_reset else '',
            'Oui' if cat.is_total else 'Non'
        ])

    writer.writerow([])
    # Feuille 2: Transactions (filtrées)
    writer.writerow(['TRANSACTIONS'])
    writer.writerow(['Date', 'Catégorie', 'Type', 'Montant', 'Avant', 'Après', 'Note', 'Par'])
    tx_qs = CashTransaction.objects.select_related('category', 'created_by').order_by('created_at')
    if category_filter:
        tx_qs = tx_qs.filter(category=category_filter)
    if start_date:
        tx_qs = tx_qs.filter(created_at__date__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__date__lte=end_date)
    for tx in tx_qs:
        writer.writerow([
            tx.created_at.strftime('%d/%m/%Y %H:%M'),
            tx.category.name,
            tx.get_transaction_type_display(),
            tx.amount,
            tx.amount_before,
            tx.amount_after,
            (tx.note or '').replace('\n', ' '),
            tx.created_by.get_full_name() if tx.created_by else 'Système'
        ])

    return response


@login_required
@user_passes_test(is_admin)
def export_cash_pdf(request):
    """Rapport PDF de caisse: par catégorie et global"""
    # Filtres
    start = request.GET.get('start')
    end = request.GET.get('end')
    category_param = request.GET.get('category')
    start_date = None
    end_date = None
    if start:
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        except Exception:
            start_date = None
    if end:
        try:
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except Exception:
            end_date = None

    response = HttpResponse(content_type='application/pdf')
    category_filter = None
    if category_param:
        try:
            category_filter = CashCategory.objects.get(id=int(category_param))
        except Exception:
            try:
                category_filter = CashCategory.objects.get(name=category_param)
            except Exception:
                category_filter = None
    suffix = f"_{category_filter.name}" if category_filter else ''
    filename = f"cash{suffix}_{datetime.now().strftime('%Y%m%d')}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()

    subtitle = 'Toutes les transactions'
    if start_date and end_date:
        subtitle = f"Du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
    elif start_date:
        subtitle = f"Depuis le {start_date.strftime('%d/%m/%Y')}"
    elif end_date:
        subtitle = f"Jusqu'au {end_date.strftime('%d/%m/%Y')}"

    pdf.add_header(elements, 'RAPPORT DE CAISSE', subtitle)

    categories = CashCategory.objects.all().order_by('-is_total', 'name')
    if category_filter:
        categories = categories.filter(id=category_filter.id)
    total_cash = sum(cat.current_amount for cat in categories if not cat.is_total)
    pdf.add_info_section(elements, {
        'Nombre de catégories': categories.count(),
        'Total (hors TOTAL)': f"{total_cash:,.0f} DA",
        'Date du rapport': datetime.now().strftime('%d/%m/%Y'),
    })

    elements.append(Spacer(1, 5))
    # Tableau des catégories
    data = [['Catégorie', 'Montant actuel', 'Dernier reset', 'TOTAL?']]
    for cat in categories:
        data.append([
            cat.name,
            f"{cat.current_amount:,.0f} DA",
            cat.last_reset.strftime('%d/%m/%Y %H:%M') if cat.last_reset else '-',
            'Oui' if cat.is_total else 'Non'
        ])
    table = pdf.create_data_table(data, col_widths=[8*cm, 5*cm, 5*cm, 3*cm], wrap_columns=[0])
    elements.append(table)

    # Transactions filtrées
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('Transactions', pdf.styles['Heading2']))
    tx_qs = CashTransaction.objects.select_related('category', 'created_by').order_by('-created_at')
    if category_filter:
        tx_qs = tx_qs.filter(category=category_filter)
    if start_date:
        tx_qs = tx_qs.filter(created_at__date__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(created_at__date__lte=end_date)
    tx_data = [['Date', 'Catégorie', 'Type', 'Montant', 'Avant', 'Après', 'Note']]
    for tx in tx_qs[:300]:
        tx_data.append([
            tx.created_at.strftime('%d/%m/%Y %H:%M'),
            tx.category.name,
            tx.get_transaction_type_display(),
            f"{tx.amount:,.0f} DA",
            f"{tx.amount_before:,.0f} DA",
            f"{tx.amount_after:,.0f} DA",
            (tx.note or '').replace('\n', ' ')
        ])
    # Largeurs généreuses pour paysage (≈24cm disponibles)
    tx_table = pdf.create_data_table(
        tx_data,
        col_widths=[3.5*cm, 4*cm, 3*cm, 3*cm, 3*cm, 3*cm, 4.5*cm],
        wrap_columns=[1, 6],
        compact=False
    )
    elements.append(tx_table)

    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def academic_year_reports_page(request):
    """Page de rapports par année académique avec filtres"""
    years = AcademicYear.objects.all().order_by('-start_date')
    year_param = request.GET.get('year')
    selected_year = None
    if year_param and year_param != 'all':
        try:
            selected_year = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            selected_year = None
    
    # Récupérer les cohorts filtrés
    cohorts_qs = Cohort.objects.select_related('academic_year', 'subject', 'level', 'teacher')
    if selected_year:
        cohorts_qs = cohorts_qs.filter(academic_year=selected_year)
    cohorts = cohorts_qs.order_by('academic_year__start_date', 'subject__name', 'name')
    
    # Statistiques
    total_enrollments = 0
    for cohort in cohorts:
        total_enrollments += cohort.enrollments.filter(is_active=True).count()
    
    context = {
        'years': years,
        'selected_year': selected_year,
        'cohorts': cohorts,
        'total_enrollments': total_enrollments,
    }
    return render(request, 'reports/academic_year_reports.html', context)


@login_required
@user_passes_test(is_admin)
def export_academic_year_pdf(request):
    """Rapport PDF global: tous les étudiants par année académique, groupés par cohort"""
    year_param = request.GET.get('year')
    selected_year = None
    if year_param and year_param != 'all':
        try:
            selected_year = AcademicYear.objects.get(id=int(year_param))
        except Exception:
            selected_year = None
    
    response = HttpResponse(content_type='application/pdf')
    suffix = f"_{selected_year.label}" if selected_year else '_toutes_annees'
    filename = f"rapport_annuel{suffix}_{datetime.now().strftime('%Y%m%d')}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    subtitle = selected_year.label if selected_year else 'Toutes les années'
    pdf.add_header(elements, 'RAPPORT ANNUEL - INSCRIPTIONS', subtitle)
    
    # Récupérer cohorts
    cohorts_qs = Cohort.objects.select_related('academic_year', 'subject', 'level', 'teacher')
    if selected_year:
        cohorts_qs = cohorts_qs.filter(academic_year=selected_year)
    cohorts = cohorts_qs.order_by('academic_year__start_date', 'subject__name', 'name')
    
    total_students = 0
    total_amount_due = 0
    total_paid = 0
    
    for cohort in cohorts:
        enrollments = cohort.enrollments.filter(is_active=True).select_related('student', 'tariff')
        if not enrollments.exists():
            continue
        
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>{cohort.name}</b> - {cohort.subject.name} ({cohort.level.name})", pdf.styles['Heading2']))
        elements.append(Paragraph(f"Année: {cohort.academic_year.label} | Professeur: {cohort.teacher.get_full_name()}", pdf.styles['Normal']))
        elements.append(Spacer(1, 3))
        
        data = [['Nom Complet', 'Email', 'Téléphone', 'Tarif', 'Payé', 'Reste']]
        for enrollment in enrollments:
            student = enrollment.student
            paid = sum(p.amount for p in enrollment.payments.all())
            balance = enrollment.balance_due
            total_students += 1
            total_amount_due += enrollment.tariff.amount
            total_paid += paid
            data.append([
                f"{student.last_name} {student.first_name}",
                student.email or '-',
                student.phone or '-',
                f"{enrollment.tariff.amount:,.0f} DA",
                f"{paid:,.0f} DA",
                f"{balance:,.0f} DA"
            ])
        
        table = pdf.create_data_table(data, col_widths=[5*cm, 5*cm, 3.5*cm, 3*cm, 3*cm, 3*cm], wrap_columns=[0, 1], compact=True)
        elements.append(table)
    
    # Synthèse globale
    elements.append(Spacer(1, 10))
    elements.append(Paragraph('<b>SYNTHÈSE GLOBALE</b>', pdf.styles['Heading2']))
    pdf.add_info_section(elements, {
        'Total étudiants': total_students,
        'Montant total attendu': f"{total_amount_due:,.0f} DA",
        'Total encaissé': f"{total_paid:,.0f} DA",
        'Reste à encaisser': f"{(total_amount_due - total_paid):,.0f} DA",
    })
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response


@login_required
@user_passes_test(is_admin)
def export_cohort_year_pdf(request, cohort_id):
    """Rapport PDF pour un cohort spécifique avec détails année académique"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"{cohort.name}_{cohort.academic_year.label}_{datetime.now().strftime('%Y%m%d')}.pdf".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
                           leftMargin=2*cm, rightMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    pdf = PDFReportBase()
    
    pdf.add_header(elements, f"RAPPORT COHORT - {cohort.name}", cohort.academic_year.label)
    
    pdf.add_info_section(elements, {
        'Groupe': cohort.name,
        'Matière': cohort.subject.name,
        'Niveau': cohort.level.name,
        'Année académique': cohort.academic_year.label,
        'Professeur': cohort.teacher.get_full_name(),
        'Période': f"{cohort.start_date.strftime('%d/%m/%Y')} - {cohort.end_date.strftime('%d/%m/%Y')}",
        'Prix standard': f"{cohort.standard_price:,.0f} DA",
    })
    
    elements.append(Spacer(1, 8))
    enrollments = cohort.enrollments.filter(is_active=True).select_related('student', 'tariff')
    
    if enrollments.exists():
        data = [['Nom Complet', 'Code', 'Email', 'Téléphone', 'Tarif', 'Payé', 'Reste']]
        total_paid = 0
        total_due = 0
        for enrollment in enrollments:
            student = enrollment.student
            paid = sum(p.amount for p in enrollment.payments.all())
            balance = enrollment.balance_due
            total_paid += paid
            total_due += enrollment.tariff.amount
            data.append([
                f"{student.last_name} {student.first_name}",
                student.student_code or '-',
                student.email or '-',
                student.phone or '-',
                f"{enrollment.tariff.amount:,.0f} DA",
                f"{paid:,.0f} DA",
                f"{balance:,.0f} DA"
            ])
        
        table = pdf.create_data_table(data, col_widths=[5*cm, 3*cm, 4*cm, 3.5*cm, 3*cm, 3*cm, 3*cm], wrap_columns=[0, 2], compact=True)
        elements.append(table)
        
        elements.append(Spacer(1, 8))
        pdf.add_info_section(elements, {
            'Total étudiants': enrollments.count(),
            'Total encaissé': f"{total_paid:,.0f} DA",
            'Reste à encaisser': f"{(total_due - total_paid):,.0f} DA",
        })
    else:
        elements.append(Paragraph("Aucun étudiant inscrit.", pdf.styles['Normal']))
    
    doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
    return response
