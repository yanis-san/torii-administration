from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    path('', views.email_dashboard, name='dashboard'),
    path('send/', views.send_email_campaign, name='send'),
    path('campaign/<int:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('copy-numbers/', views.copy_numbers_page, name='copy_numbers'),
    
    # API endpoints
    path('api/cohort/<int:cohort_id>/recipients/', views.get_cohort_recipients, name='api_cohort_recipients'),
    path('api/all-recipients/', views.get_all_recipients, name='api_all_recipients'),
    path('api/cohort/<int:cohort_id>/phone-numbers/', views.get_cohort_phone_numbers, name='api_cohort_phone_numbers'),
]
