from django.urls import path
from . import views

app_name = 'certificate'

urlpatterns = [
    # Liste des cohorts éligibles
    path('', views.certificate_cohort_list, name='cohort_list'),
    
    # Générer les documents (certificats + attestations) pour un cohort
    path('generate/<int:cohort_id>/', views.generate_certificates_view, name='generate'),
    
    # Télécharger tous les documents en ZIP (par cohort)
    path('download/<int:cohort_id>/', views.download_certificates_zip, name='download_zip'),
    
    # Prévisualiser/télécharger un certificat individuel
    path('preview/<int:cohort_id>/<int:student_id>/', views.preview_certificate, name='preview'),
    
    # Télécharger une attestation individuelle
    path('attestation/<int:cohort_id>/<int:student_id>/', views.preview_attestation, name='attestation'),
    
    # Télécharger le dossier complet d'un étudiant (certificat + attestation) en ZIP
    path('student-zip/<int:cohort_id>/<int:student_id>/', views.download_student_zip, name='student_zip'),
    
    # API pour génération AJAX
    path('api/generate/<int:cohort_id>/', views.api_generate_certificates, name='api_generate'),
]
