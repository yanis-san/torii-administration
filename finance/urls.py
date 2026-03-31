from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'finance'

urlpatterns = [
    # Paiements étudiants
    path('payment/add/<int:enrollment_id>/', views.add_payment, name='add_payment'),
    path('payment/delete/<int:payment_id>/', views.delete_payment, name='delete_payment'),
    path('payment/edit/<int:payment_id>/', views.edit_payment, name='edit_payment'),
    
    # Dashboard paiements
    path('payments-dashboard/', views.payment_status_dashboard, name='payment_status_dashboard'),

    # Paie des professeurs (ancien système)
    # Legacy route redirected to the new cohort payroll
    path('payroll/', RedirectView.as_view(pattern_name='finance:teacher_cohort_payroll', permanent=True), name='teacher_payroll_list'),
    path('payroll/teacher/<int:teacher_id>/', views.teacher_payroll_detail, name='teacher_payroll_detail'),
    path('payroll/teacher/<int:teacher_id>/pay/', views.record_teacher_payment, name='record_teacher_payment'),
    
    # Paie par cohort (nouveau système - TDD)
    path('payroll-cohort/', views.teacher_cohort_payroll, name='teacher_cohort_payroll'),
    path('payroll-cohort/<int:cohort_id>/', views.teacher_cohort_payment_detail, name='teacher_cohort_payment_detail'),
    path('payroll-cohort/<int:cohort_id>/pay/', views.record_cohort_payment, name='record_cohort_payment'),
]