# school_management/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import dashboard, login_view, logout_view, signup_view, academic_year_list, backups_and_recovery, backup_start, backup_progress, backup_result, download_schedule_pdf
from students.views import create_enrollment

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup_view, name='signup'),
    path('', dashboard, name='dashboard'),
    path('academic-years/', academic_year_list, name='academic_year_list'),
    path('backups/', backups_and_recovery, name='backups_and_recovery'),
    path('backup/start/', backup_start, name='backup_start'),
    path('backup/progress/', backup_progress, name='backup_progress'),
    path('backup/result/', backup_result, name='backup_result'),
    path('schedule/pdf/', download_schedule_pdf, name='download_schedule_pdf'),
    path('enrollment/new/', create_enrollment, name='create_enrollment'),
    path('students/', include('students.urls')),
    path('prospects/', include('prospects.urls')),
    path('finance/', include('finance.urls')),
    path('academics/', include('academics.urls')),
    path('documents/', include('documents.urls')),
    path('cash/', include('cash.urls')),
    path('reports/', include('reports.urls')),
    path('emails/', include('emails.urls')),
    path('inventory/', include('inventory.urls')),
    path('tasks/', include('tasks.urls')),
    path('certificates/', include('certificate.urls')),
]

# Serve media files in development and optionally in production (fallback mode)
if settings.DEBUG or getattr(settings, 'SERVE_MEDIA_WITH_DJANGO', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]