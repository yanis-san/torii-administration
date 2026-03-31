# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.select_cohort, name='select_cohort'),
    path('global/', views.global_reports, name='global_reports'),
    path('cohorts/<int:cohort_id>/report/', views.cohort_report, name='cohort_report'),

    # Page dédiée synchronisation
    path('sync/', views.sync_page, name='sync_page'),
    path('sync/history/', views.sync_history, name='sync_history'),
    path('sync/detail/<int:sync_id>/', views.sync_detail, name='sync_detail'),
    
    # ZIPs
    path('cohorts/<int:cohort_id>/zip/', views.download_cohort_zip, name='download_cohort_zip'),
    path('all-cohorts/zip/', views.download_all_cohorts_zip, name='download_all_cohorts_zip'),

    # Synchronisation multi-utilisateurs
    path('sync/export/<int:cohort_id>/<str:data_type>/', views.export_sync_csv, name='export_sync_csv'),
    path('sync/import/<int:cohort_id>/<str:data_type>/', views.import_sync_csv, name='import_sync_csv'),
    
    # Synchronisation GLOBALE (tous les cohortes)
    path('sync/global/export/', views.export_global_sync, name='export_global_sync'),
    path('sync/global/import/', views.import_global_sync, name='import_global_sync'),

    # Téléchargement individuel des listes de présence
    path('attendance/session/<int:session_id>/', views.download_session_attendance, name='download_session_attendance'),
    path('attendance/cohort/<int:cohort_id>/', views.download_cohort_attendance, name='download_cohort_attendance'),
    
    # Dossiers complets
    path('student/<int:student_id>/complete/', views.download_student_complete_pdf, name='download_student_complete'),
    path('cohort/<int:cohort_id>/complete/', views.download_cohort_complete_zip, name='download_cohort_complete'),
    path('cohort/<int:cohort_id>/payment-report/', views.download_cohort_payment_report, name='download_cohort_payment_report'),
    path('all-cohorts/payment-report/', views.download_all_cohorts_payment_report, name='download_all_cohorts_payment_report'),
    
    # Professeurs
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('teachers/<int:teacher_id>/download/', views.download_teacher_document, name='download_teacher_document'),
]

