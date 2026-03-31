"""
Vue pour générer tous les rapports en ZIP
"""
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm
from datetime import datetime, date, timedelta
import zipfile
import io
from collections import defaultdict

from .pdf_utils import PDFReportBase
from students.models import Student, Enrollment
from academics.models import Cohort, CourseSession
from finance.models import Payment


def is_admin(user):
    """Vérifier si l'utilisateur est admin (pas professeur)"""
    return user.is_authenticated and not user.is_teacher


@login_required
@user_passes_test(is_admin)
def generate_all_reports_zip(request):
    """Générer tous les rapports dans un fichier ZIP"""
    # Récupérer les paramètres de période (par défaut: mois courant)
    period_start = request.GET.get('start')
    period_end = request.GET.get('end')
    
    if not period_start or not period_end:
        # Par défaut: mois courant
        today = date.today()
        period_start = today.replace(day=1)
        last_day = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        period_end = last_day
    else:
        try:
            period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
        except:
            today = date.today()
            period_start = today.replace(day=1)
            last_day = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            period_end = last_day
    
    # Créer un buffer pour le ZIP
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Rapport de tous les étudiants
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=PDFReportBase().pagesize,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        pdf = PDFReportBase()
        
        pdf.add_header(elements, "LISTE COMPLÈTE DES ÉTUDIANTS", 
                      f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}")
        
        active_student_ids = Enrollment.objects.filter(
            is_active=True,
            date__lte=period_end
        ).values_list('student_id', flat=True).distinct()
        
        pdf.add_info_section(elements, {
            'Période': f"{period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')}",
            'Nombre d\'étudiants': active_student_ids.count(),
        })
        
        elements.append(Spacer(1, 5))
        
        students = Student.objects.filter(id__in=active_student_ids).order_by('last_name', 'first_name')
        
        if students.exists():
            data = [['Nom Complet', 'Email', 'Téléphone', 'Inscriptions']]
            for student in students:
                enrollments_count = student.enrollments.filter(is_active=True).count()
                data.append([
                    f"{student.last_name} {student.first_name}",
                    student.email or '-',
                    student.phone or '-',
                    str(enrollments_count)
                ])
            table = pdf.create_data_table(data, col_widths=[5*cm, 5*cm, 3.5*cm, 2.5*cm], wrap_columns=[0, 1])
            elements.append(table)
        else:
            elements.append(Paragraph("Aucun étudiant actif trouvé.", pdf.styles['Normal']))
        
        doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
        zip_file.writestr(f"1_etudiants_complet_{period_start.strftime('%Y%m%d')}.pdf", pdf_buffer.getvalue())
        
        # 2. Rapports par cohort (étudiants + séances)
        cohorts = Cohort.objects.filter(
            Q(start_date__lte=period_end) & Q(end_date__gte=period_start)
        ).select_related('subject', 'level', 'teacher')
        
        for idx, cohort in enumerate(cohorts, start=2):
            # 2.a) Étudiants du cohort
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=PDFReportBase().pagesize,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            pdf = PDFReportBase()
            
            pdf.add_header(elements, f"ÉTUDIANTS - {cohort.name}",
                          f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}")
            
            pdf.add_info_section(elements, {
                'Groupe': cohort.name,
                'Matière': cohort.subject.name,
                'Niveau': cohort.level.name,
                'Professeur': cohort.teacher.get_full_name(),
                'Période': f"{cohort.start_date.strftime('%d/%m/%Y')} - {cohort.end_date.strftime('%d/%m/%Y')}",
                'Prix standard': f"{cohort.standard_price} DA",
            })
            
            elements.append(Spacer(1, 5))
            
            enrollments = cohort.enrollments.filter(is_active=True).select_related('student', 'tariff')
            
            if enrollments.exists():
                data = [['Nom Complet', 'Email', 'Téléphone', 'Prix Convenu', 'Payé', 'Reste']]
                for enrollment in enrollments:
                    student = enrollment.student
                    balance = enrollment.balance_due
                    total_paid = sum(p.amount for p in enrollment.payments.all())
                    data.append([
                        f"{student.last_name} {student.first_name}",
                        student.email or '-',
                        student.phone or '-',
                        f"{enrollment.tariff.amount} DA",
                        f"{total_paid} DA",
                        f"{balance} DA"
                    ])
                table = pdf.create_data_table(data, col_widths=[4*cm, 4*cm, 3*cm, 2.5*cm, 2.5*cm, 2*cm], wrap_columns=[0, 1])
                elements.append(table)
            else:
                elements.append(Paragraph("Aucun étudiant inscrit dans ce groupe.", pdf.styles['Normal']))
            
            doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
            safe_name = cohort.name.replace('/', '-').replace('\\', '-')
            zip_file.writestr(f"{idx}a_etudiants_{safe_name}.pdf", pdf_buffer.getvalue())
            
            # 2.b) Séances du cohort
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(pdf_buffer, pagesize=PDFReportBase().pagesize,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            pdf = PDFReportBase()
            
            pdf.add_header(elements, f"SÉANCES - {cohort.name}",
                          f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}")
            
            sessions = CourseSession.objects.filter(
                cohort=cohort,
                date__gte=period_start,
                date__lte=period_end
            ).select_related('teacher').order_by('date')
            
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
            
            if sessions.exists():
                data = [['Date', 'Horaire', 'Professeur', 'Statut', 'Note']]
                
                for session in sessions:
                    teacher_name = session.teacher.get_full_name()
                    if session.teacher.id != cohort.teacher.id:
                        teacher_name += " (Remplaçant)"
                    
                    status_map = {
                        'SCHEDULED': 'Prévu',
                        'COMPLETED': 'Terminé',
                        'CANCELLED': 'Annulé',
                        'POSTPONED': 'Reporté'
                    }
                    status = status_map.get(session.status, session.status)
                    
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
                
                table = pdf.create_data_table(data, col_widths=[3*cm, 3*cm, 5*cm, 2.5*cm, 3.5*cm], wrap_columns=[2, 4])
                elements.append(table)
            else:
                elements.append(Paragraph("Aucune séance programmée.", pdf.styles['Normal']))
            
            doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
            zip_file.writestr(f"{idx}b_seances_{safe_name}.pdf", pdf_buffer.getvalue())
        
        # 3. Rapport des paiements
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=PDFReportBase().pagesize,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        pdf = PDFReportBase()
        
        pdf.add_header(elements,
                       f"RAPPORT DES PAIEMENTS",
                       f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}")
        
        payments = Payment.objects.filter(
            date__gte=period_start,
            date__lte=period_end
        ).select_related('enrollment__student', 'enrollment__cohort', 'recorded_by').order_by('date')
        
        total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        pdf.add_info_section(elements, {
            'Période': f"{period_start.strftime('%d/%m/%Y')} - {period_end.strftime('%d/%m/%Y')}",
            'Nombre de paiements': payments.count(),
            'Montant total': f"{total_amount:,.0f} DA",
        })
        
        elements.append(Spacer(1, 5))
        
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
            
            table = pdf.create_data_table(data, col_widths=[2.5*cm, 4*cm, 4.5*cm, 2.5*cm, 3.5*cm], wrap_columns=[1, 2, 4])
            elements.append(table)
        else:
            elements.append(Paragraph("Aucun paiement enregistré pour cette période.", pdf.styles['Normal']))
        
        doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
        zip_file.writestr(f"9998_paiements_{period_start.strftime('%Y%m%d')}.pdf", pdf_buffer.getvalue())
        
        # 4. Rapport de paie des professeurs
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=PDFReportBase().pagesize,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        elements = []
        pdf = PDFReportBase()
        
        pdf.add_header(elements, "RAPPORT DE PAIE PROFESSEURS",
                      f"Du {period_start.strftime('%d/%m/%Y')} au {period_end.strftime('%d/%m/%Y')}")
        
        cohorts_all = Cohort.objects.select_related('teacher').all()
        payroll_data = []
        
        for cohort in cohorts_all:
            sessions_query = CourseSession.objects.filter(
                cohort=cohort,
                status='COMPLETED',
                date__gte=period_start,
                date__lte=period_end
            ).select_related('teacher')
            
            sessions = sessions_query
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
            
            table = pdf.create_data_table(data, col_widths=[4.5*cm, 5*cm, 2*cm, 2*cm, 3.5*cm], wrap_columns=[0, 1])
            elements.append(table)
        else:
            elements.append(Paragraph("Aucune donnée de paie disponible.", pdf.styles['Normal']))
        
        doc.build(elements, onFirstPage=pdf.add_footer, onLaterPages=pdf.add_footer)
        zip_file.writestr(f"9999_paie_professeurs_{period_start.strftime('%Y%m%d')}.pdf", pdf_buffer.getvalue())
    
    # Retourner le ZIP
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    filename = f"rapports_complets_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}.zip"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
