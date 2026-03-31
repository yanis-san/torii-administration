"""
Vues pour la génération et le téléchargement de certificats et attestations.
"""
import os
import io
import zipfile
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404, FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages

from academics.models import Cohort
from .generator import generate_documents_for_cohort, detect_language_from_subject


def is_admin(user):
    """Vérifier si l'utilisateur est admin (pas professeur)"""
    return user.is_authenticated and not user.is_teacher


@login_required
@user_passes_test(is_admin)
def certificate_cohort_list(request):
    """
    Page listant les cohorts éligibles pour la génération de certificats/attestations.
    Seuls les cohorts avec une langue supportée (Chinois, Coréen, Japonais) sont affichés.
    """
    cohorts = Cohort.objects.select_related('subject', 'level', 'teacher').order_by('-start_date')
    
    # Filtrer les cohorts avec langues supportées et ajouter des infos
    eligible_cohorts = []
    for cohort in cohorts:
        language = detect_language_from_subject(cohort.subject.name)
        if language:
            # Compter les séances validées
            completed_sessions = cohort.sessions.filter(status='COMPLETED').count()
            total_sessions = cohort.sessions.count()
            
            # Compter les étudiants actifs
            active_enrollments = cohort.enrollments.filter(is_active=True).count()
            
            eligible_cohorts.append({
                'cohort': cohort,
                'language': language,
                'language_display': {'cn': 'Chinois', 'kr': 'Coréen', 'jp': 'Japonais'}.get(language, language),
                'completed_sessions': completed_sessions,
                'total_sessions': total_sessions,
                'active_students': active_enrollments,
                'can_generate': completed_sessions > 0 and active_enrollments > 0,
            })
    
    context = {
        'cohorts': eligible_cohorts,
    }
    return render(request, 'certificate/cohort_list.html', context)


@login_required
@user_passes_test(is_admin)
def generate_certificates_view(request, cohort_id):
    """
    Génère les certificats et attestations pour un cohort et affiche un récapitulatif.
    """
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Vérifier que la langue est supportée
    language = detect_language_from_subject(cohort.subject.name)
    if not language:
        messages.error(request, f"Langue non supportée pour les certificats: {cohort.subject.name}")
        return render(request, 'certificate/generation_result.html', {'cohort': cohort, 'error': True})
    
    # Générer les documents (certificats + attestations)
    result = generate_documents_for_cohort(cohort, min_attendance_ratio=0.5)
    
    context = {
        'cohort': cohort,
        'result': result,
        'generated_count': len(result['generated']),
        'skipped_count': len(result['skipped']),
        'language_display': {'cn': 'Chinois', 'kr': 'Coréen', 'jp': 'Japonais'}.get(language, language),
    }
    
    if result['generated']:
        messages.success(request, f"✅ {len(result['generated'])} dossier(s) généré(s) (certificat + attestation)!")
    
    if result['skipped']:
        messages.warning(request, f"⚠️ {len(result['skipped'])} étudiant(s) non éligible(s)")
    
    return render(request, 'certificate/generation_result.html', context)


@login_required
@user_passes_test(is_admin)
def download_certificates_zip(request, cohort_id):
    """
    Télécharge tous les documents (certificats + attestations) d'un cohort dans un fichier ZIP.
    Structure: NomEtudiant/certificat.png + attestation.docx
    """
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Générer les documents
    result = generate_documents_for_cohort(cohort, min_attendance_ratio=0.5)
    
    if not result['generated']:
        messages.error(request, "Aucun document à télécharger.")
        return HttpResponse("Aucun document généré.", status=404)
    
    # Créer le ZIP en mémoire
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for student, cert_path, attest_path, presences, total in result['generated']:
            # Nom du dossier étudiant dans le ZIP
            student_folder = f"{student.first_name}_{student.last_name}".replace(' ', '_')
            
            # Ajouter le certificat PNG
            if cert_path and os.path.exists(cert_path):
                cert_filename = os.path.basename(cert_path)
                zip_file.write(cert_path, f"{student_folder}/{cert_filename}")
            
            # Ajouter l'attestation Word
            if attest_path and os.path.exists(attest_path):
                attest_filename = os.path.basename(attest_path)
                zip_file.write(attest_path, f"{student_folder}/{attest_filename}")
    
    zip_buffer.seek(0)
    
    # Nom du fichier ZIP
    safe_name = cohort.abbreviation or f"cohort_{cohort.id}"
    date_str = datetime.now().strftime('%Y%m%d')
    zip_filename = f"documents_{safe_name}_{date_str}.zip"
    
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    
    return response


@login_required
@user_passes_test(is_admin)
def preview_certificate(request, cohort_id, student_id):
    """
    Prévisualise/télécharge un certificat individuel.
    """
    from students.models import Student
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    student = get_object_or_404(Student, id=student_id)
    
    # Construire le chemin du certificat
    language = detect_language_from_subject(cohort.subject.name)
    if not language:
        raise Http404("Langue non supportée")
    
    safe_cohort_name = cohort.abbreviation or f"cohort_{cohort.id}"
    student_folder = f"{student.first_name}_{student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
    clean_name = f"{student.first_name} {student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"certificat_{language}_{clean_name}.png"
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cert_path = os.path.join(BASE_DIR, 'certificate', 'generated', safe_cohort_name, student_folder, filename)
    
    if not os.path.exists(cert_path):
        raise Http404("Certificat non trouvé. Veuillez d'abord générer les documents.")
    
    return FileResponse(open(cert_path, 'rb'), content_type='image/png')


@login_required
@user_passes_test(is_admin)
def preview_attestation(request, cohort_id, student_id):
    """
    Télécharge une attestation Word individuelle.
    """
    from students.models import Student
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    student = get_object_or_404(Student, id=student_id)
    
    safe_cohort_name = cohort.abbreviation or f"cohort_{cohort.id}"
    student_folder = f"{student.first_name}_{student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
    clean_name = f"{student.first_name} {student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"attestation_{clean_name}.docx"
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    attest_path = os.path.join(BASE_DIR, 'certificate', 'generated', safe_cohort_name, student_folder, filename)
    
    if not os.path.exists(attest_path):
        raise Http404("Attestation non trouvée. Veuillez d'abord générer les documents.")
    
    response = FileResponse(open(attest_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(is_admin)
def download_student_zip(request, cohort_id, student_id):
    """
    Télécharge le dossier complet d'un étudiant (certificat + attestation) en ZIP.
    """
    from students.models import Student
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    student = get_object_or_404(Student, id=student_id)
    
    language = detect_language_from_subject(cohort.subject.name)
    if not language:
        raise Http404("Langue non supportée")
    
    safe_cohort_name = cohort.abbreviation or f"cohort_{cohort.id}"
    student_folder = f"{student.first_name}_{student.last_name}".replace(' ', '_').replace('/', '_').replace('\\', '_')
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    student_dir = os.path.join(BASE_DIR, 'certificate', 'generated', safe_cohort_name, student_folder)
    
    if not os.path.exists(student_dir):
        raise Http404("Dossier étudiant non trouvé. Veuillez d'abord générer les documents.")
    
    # Créer le ZIP
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in os.listdir(student_dir):
            file_path = os.path.join(student_dir, file)
            if os.path.isfile(file_path):
                zip_file.write(file_path, file)
    
    zip_buffer.seek(0)
    
    zip_filename = f"{student_folder}_documents.zip"
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    
    return response


@login_required
@user_passes_test(is_admin)
def api_generate_certificates(request, cohort_id):
    """
    API endpoint pour générer les documents (AJAX).
    Retourne un JSON avec le résultat.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    cohort = get_object_or_404(Cohort, id=cohort_id)
    
    # Générer les documents
    result = generate_documents_for_cohort(cohort, min_attendance_ratio=0.5)
    
    return JsonResponse({
        'success': True,
        'cohort_name': cohort.name,
        'cohort_abbreviation': cohort.abbreviation,
        'language': result['language'],
        'level': result['level'],
        'total_sessions': result['total_sessions'],
        'start_date': result['start_date'].isoformat() if result['start_date'] else None,
        'end_date': result['end_date'].isoformat() if result['end_date'] else None,
        'generated_count': len(result['generated']),
        'skipped_count': len(result['skipped']),
        'generated': [
            {
                'student_name': f"{s.first_name} {s.last_name}",
                'student_id': s.id,
                'has_certificate': cert_path is not None,
                'has_attestation': attest_path is not None,
                'presences': presences,
                'total': total,
                'ratio': f"{(presences/total)*100:.1f}%" if total > 0 else "0%"
            }
            for s, cert_path, attest_path, presences, total in result['generated']
        ],
        'skipped': [
            {
                'student_name': f"{s.first_name} {s.last_name}" if s else "N/A",
                'reason': reason
            }
            for s, reason in result['skipped']
        ],
    })
