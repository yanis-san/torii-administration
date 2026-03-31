#!/usr/bin/env python
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from academics.models import CourseSession, Cohort
from core.models import TeacherProfile, User
from students.models import Student, Enrollment

print("=" * 80)
print("DIAGNOSTIC: Vérification des données de séances")
print("=" * 80)

# 1. Afficher tous les cohorts
print("\n📚 COHORTS:")
for cohort in Cohort.objects.all():
    print(f"  • {cohort.name} - Prof: {cohort.teacher.get_full_name()} - Tarif: {cohort.teacher_hourly_rate} DA/h")

# 2. Afficher toutes les séances
print("\n📅 SÉANCES:")
sessions = CourseSession.objects.all().order_by('-date')
for session in sessions[:20]:  # Afficher les 20 dernières
    print(f"  • {session.date} ({session.start_time}-{session.end_time}) - {session.cohort.name} - Status: {session.status}")

# 3. Afficher les séances pour une période spécifique
print("\n🔍 SÉANCES PÉRIODE (01/11/2025 - 30/11/2025):")
start = datetime(2025, 11, 1).date()
end = datetime(2025, 11, 30).date()
sessions_in_period = CourseSession.objects.filter(date__gte=start, date__lte=end, status='COMPLETED')
print(f"  Séances trouvées: {sessions_in_period.count()}")
for session in sessions_in_period:
    print(f"    • {session.date} - {session.cohort.name} - {session.status}")

# 4. Afficher les profs et leurs profils
print("\n👨‍🏫 PROFESSEURS:")
for teacher in User.objects.filter(groups__name='Teacher'):
    profile = teacher.teacherprofile if hasattr(teacher, 'teacherprofile') else None
    if profile:
        print(f"  • {teacher.get_full_name()} - Fréquence: {profile.get_payment_frequency_display()}")
    else:
        print(f"  • {teacher.get_full_name()} - Pas de profil teacher")

print("\n" + "=" * 80)
