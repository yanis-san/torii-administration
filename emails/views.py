from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import Q

from academics.models import Cohort
from students.models import Student, Enrollment
from .models import EmailCampaign


def is_admin(user):
    """Vérifier si l'utilisateur est admin"""
    return user.is_authenticated and not user.is_teacher


@login_required
@user_passes_test(is_admin)
def email_dashboard(request):
    """Page principale d'envoi d'emails groupés"""
    cohorts = Cohort.objects.filter(academic_year__is_current=True).select_related('subject', 'level', 'teacher').order_by('subject__name', 'name')
    recent_campaigns = EmailCampaign.objects.select_related('cohort', 'sent_by').all()[:10]
    
    context = {
        'cohorts': cohorts,
        'recent_campaigns': recent_campaigns,
    }
    return render(request, 'emails/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def get_cohort_recipients(request, cohort_id):
    """API: Récupérer la liste des emails d'un cohort"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Récupérer les étudiants inscrits (actifs ou non, selon le paramètre)
    active_only = request.GET.get('active_only', 'true').lower() == 'true'
    
    enrollments = cohort.enrollments.select_related('student')
    if active_only:
        enrollments = enrollments.filter(is_active=True)
    
    students = [e.student for e in enrollments]
    emails = [s.email for s in students if s.email]
    
    return JsonResponse({
        'cohort_name': cohort.name,
        'total_students': len(students),
        'emails': emails,
        'count': len(emails)
    })


@login_required
@user_passes_test(is_admin)
def get_all_recipients(request):
    """API: Récupérer tous les emails des étudiants"""
    active_only = request.GET.get('active_only', 'true').lower() == 'true'
    
    if active_only:
        # Étudiants avec au moins une inscription active
        student_ids = Enrollment.objects.filter(is_active=True).values_list('student_id', flat=True).distinct()
        students = Student.objects.filter(id__in=student_ids)
    else:
        # Tous les étudiants
        students = Student.objects.all()
    
    emails = [s.email for s in students if s.email]
    
    return JsonResponse({
        'total_students': students.count(),
        'emails': emails,
        'count': len(emails),
        'active_only': active_only
    })


@login_required
@user_passes_test(is_admin)
def send_email_campaign(request):
    """Envoyer un email groupé (pour l'instant console backend)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        recipient_type = request.POST.get('recipient_type')
        cohort_id = request.POST.get('cohort_id')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        active_only = request.POST.get('active_only', 'true').lower() == 'true'
        
        # Validation
        if not subject or not message:
            return JsonResponse({'error': 'Sujet et message requis'}, status=400)
        
        # Récupérer les destinataires
        recipients = []
        cohort = None
        
        if recipient_type == 'COHORT':
            if not cohort_id:
                return JsonResponse({'error': 'Cohort requis pour ce type d\'envoi'}, status=400)
            cohort = get_object_or_404(Cohort, id=cohort_id)
            enrollments = cohort.enrollments.select_related('student')
            if active_only:
                enrollments = enrollments.filter(is_active=True)
            recipients = [e.student.email for e in enrollments if e.student.email]
        
        elif recipient_type == 'ALL_ACTIVE':
            student_ids = Enrollment.objects.filter(is_active=True).values_list('student_id', flat=True).distinct()
            students = Student.objects.filter(id__in=student_ids)
            recipients = [s.email for s in students if s.email]
        
        elif recipient_type == 'ALL_STUDENTS':
            students = Student.objects.all()
            recipients = [s.email for s in students if s.email]
        
        else:
            return JsonResponse({'error': 'Type de destinataires invalide'}, status=400)
        
        if not recipients:
            return JsonResponse({'error': 'Aucun destinataire trouvé'}, status=400)
        
        # Créer la campagne
        campaign = EmailCampaign.objects.create(
            title=f"Email {recipient_type} - {subject[:50]}",
            recipient_type=recipient_type,
            cohort=cohort,
            subject=subject,
            message=message,
            sent_by=request.user,
            total_recipients=len(recipients),
            recipient_emails=', '.join(recipients)
        )
        
        # Envoyer l'email (backend console pour l'instant)
        success_count = 0
        failure_count = 0
        recipient_details = {}
        
        from datetime import datetime
        
        try:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[],
                bcc=recipients,  # BCC pour envoi groupé
            )
            
            # Pièce jointe si présente
            if 'attachment' in request.FILES:
                attachment_file = request.FILES['attachment']
                email.attach(attachment_file.name, attachment_file.read(), attachment_file.content_type)
                campaign.attachment = attachment_file
                campaign.save()
            
            email.send(fail_silently=False)
            success_count = len(recipients)
            
            # Enregistrer le succès pour chaque destinataire
            sent_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            for recipient in recipients:
                recipient_details[recipient] = {
                    'status': 'success',
                    'sent_at': sent_time,
                    'error': None
                }
            
        except Exception as e:
            failure_count = len(recipients)
            error_msg = str(e)
            
            # Enregistrer l'échec pour chaque destinataire
            sent_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            for recipient in recipients:
                recipient_details[recipient] = {
                    'status': 'failed',
                    'sent_at': sent_time,
                    'error': error_msg
                }
            
            messages.error(request, f"Erreur lors de l'envoi: {error_msg}")
        
        # Mettre à jour les statistiques
        campaign.success_count = success_count
        campaign.failure_count = failure_count
        campaign.recipient_details = recipient_details
        campaign.save()
        
        if success_count > 0:
            messages.success(request, f"Email envoyé à {success_count} destinataire(s) !")
        
        return redirect('emails:dashboard')
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def campaign_detail(request, campaign_id):
    """Détail d'une campagne d'email"""
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    
    # Préparer les données des destinataires avec leurs détails
    recipients_data = []
    if campaign.recipient_details:
        for email, details in campaign.recipient_details.items():
            recipients_data.append({
                'email': email,
                'status': details.get('status', 'unknown'),
                'sent_at': details.get('sent_at', ''),
                'error': details.get('error', '')
            })
    else:
        # Fallback si pas de recipient_details (anciennes campagnes)
        for email in (campaign.recipient_emails.split(', ') if campaign.recipient_emails else []):
            recipients_data.append({
                'email': email,
                'status': 'unknown',
                'sent_at': '',
                'error': ''
            })
    
    # Trier par statut (failed d'abord)
    recipients_data.sort(key=lambda x: (x['status'] != 'failed', x['email']))
    
    context = {
        'campaign': campaign,
        'recipients_data': recipients_data,
        'success_recipients': [r for r in recipients_data if r['status'] == 'success'],
        'failed_recipients': [r for r in recipients_data if r['status'] == 'failed'],
    }
    return render(request, 'emails/campaign_detail.html', context)


@login_required
@user_passes_test(is_admin)
def copy_numbers_page(request):
    """Page pour copier facilement les numéros de téléphone d'un cohort"""
    cohorts = Cohort.objects.filter(academic_year__is_current=True).select_related('subject', 'level').order_by('subject__name', 'name')
    
    context = {
        'cohorts': cohorts,
    }
    return render(request, 'emails/copy_numbers.html', context)


@login_required
@user_passes_test(is_admin)
def get_cohort_phone_numbers(request, cohort_id):
    """API: Récupérer les numéros de téléphone d'un cohort formatés pour copie"""
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Récupérer les étudiants inscrits avec téléphone
    enrollments = cohort.enrollments.select_related('student').filter(is_active=True)
    
    students = []
    phone_numbers = []
    
    for enrollment in enrollments:
        student = enrollment.student
        # Vérifier que l'étudiant a un numéro de téléphone
        if student.phone:
            phone = student.phone.strip()
            # Formater le numéro (enlever espaces, tirets, etc.)
            phone_clean = ''.join(filter(str.isdigit, phone))
            if phone_clean:
                phone_numbers.append(phone_clean)
                students.append({
                    'name': f"{student.last_name.upper()} {student.first_name}",
                    'phone': phone,
                    'phone_clean': phone_clean
                })
    
    return JsonResponse({
        'cohort_name': cohort.name,
        'total_students': len(phone_numbers),
        'phone_numbers': phone_numbers,
        'phone_numbers_formatted': ','.join(phone_numbers),
        'students': students,
    })
