from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list, name='list'),
    path('<int:pk>/', views.student_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_student, name='edit'),
    path('<int:pk>/delete/', views.delete_student, name='delete'),
    path('<int:pk>/toggle-annual-fee/', views.toggle_annual_fee, name='toggle_annual_fee'),
    path('enrollment/form/', views.enrollment_form, name='enrollment_form'),
    path('enrollment/<int:enrollment_id>/edit-tariff/', views.enrollment_edit_tariff, name='edit_tariff'),
    path('enrollment/<int:enrollment_id>/unenroll/', views.unenroll_enrollment, name='unenroll'),
    path('enrollment/<int:enrollment_id>/delete/', views.delete_enrollment, name='delete_enrollment'),
    path('<int:pk>/export/history.csv', views.export_student_history_csv, name='export_history'),
]