from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Menu principal
    path('', views.reports_menu, name='menu'),
    # Rapports annuels (année académique)
    path('annual/', views.annual_reports_page, name='annual_menu'),
    path('annual/enrollments/pdf/', views.report_enrollments_by_academic_year, name='annual_enrollments_pdf'),
    path('annual/enrollments/csv/', views.export_enrollments_by_academic_year_csv, name='annual_enrollments_csv'),
    path('annual/enrollments/zip/', views.report_enrollments_by_academic_year_zip, name='annual_enrollments_zip'),
    # Frais d'inscription annuels (non payés)
    path('annual/fees/unpaid/pdf/', views.report_unpaid_annual_fees_pdf, name='annual_fees_unpaid_pdf'),
    path('annual/fees/unpaid/csv/', views.export_unpaid_annual_fees_csv, name='annual_fees_unpaid_csv'),
    # Page rapports cash avec onglets
    path('cash/', views.cash_reports_page, name='cash_page'),
    # Exports cash
    path('cash/export/pdf/', views.export_cash_pdf, name='cash_export_pdf'),
    path('cash/export/csv/', views.export_cash_csv, name='cash_export_csv'),
    
    # Rapports par année académique
    path('academic-year/', views.academic_year_reports_page, name='academic_year_page'),
    path('academic-year/pdf/', views.export_academic_year_pdf, name='academic_year_pdf'),
    path('academic-year/cohort/<int:cohort_id>/pdf/', views.export_cohort_year_pdf, name='cohort_year_pdf'),
    
    # Rapports étudiants
    path('students/all/', views.report_all_students, name='students_all'),
    path('students/cohort/<int:cohort_id>/', views.report_cohort_students, name='cohort_students'),
    
    # Rapports séances
    path('sessions/cohort/<int:cohort_id>/', views.report_cohort_sessions, name='cohort_sessions'),
    
    # Rapports paiements
    path('payments/monthly/', views.report_payments_monthly, name='payments_monthly'),
    path('payroll/teachers/', views.report_teacher_payroll, name='teacher_payroll'),
    path('students/retained.csv', views.export_retained_students_csv, name='retained_students_csv'),
    
    # Générer tous les rapports en ZIP
    path('all/zip/', views.generate_all_reports_zip, name='all_zip'),
]
