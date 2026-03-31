from django.urls import path
from . import views


app_name = 'academics'

urlpatterns = [
    path('cohorts/', views.cohort_list, name='list'),
    path('cohorts/<int:pk>/', views.cohort_detail, name='detail'),
    path('cohorts/<int:pk>/generate/', views.generate_sessions, name='generate_sessions'),
    path('cohorts/<int:pk>/finish/', views.finish_cohort, name='finish_cohort'),
    path('cohorts/<int:cohort_id>/add-session/', views.add_session_manual, name='add_session'),
    
    # --- NOUVELLE ROUTE ---
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('session/<int:session_id>/postpone/', views.postpone_session, name='postpone_session'),
    path('session/<int:session_id>/cancel-postpone/', views.cancel_postpone, name='cancel_postpone'),
    path('session/<int:session_id>/change-teacher/', views.change_session_teacher, name='change_session_teacher'),
]
