from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='list'),
    path('calendar/', views.task_calendar, name='calendar'),
    path('calendar/<int:year>/<int:month>/<int:day>/', views.tasks_by_day, name='day_detail'),
    path('create/', views.task_create, name='create'),
    path('<int:task_id>/toggle/', views.task_toggle_complete, name='toggle_complete'),
    path('<int:task_id>/delete/', views.task_delete, name='delete'),
    path('<int:task_id>/edit/', views.task_edit, name='edit'),
    path('search-person/', views.search_person, name='search_person'),
]
