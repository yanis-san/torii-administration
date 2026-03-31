#!/usr/bin/env python
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from academics.models import CourseSession, Cohort

print("=" * 80)
print("DATES RÉELLES DES COHORTS")
print("=" * 80)

for cohort in Cohort.objects.all():
    sessions = CourseSession.objects.filter(cohort=cohort).order_by('date')
    if sessions.exists():
        first_session = sessions.first().date
        last_session = sessions.last().date
        print(f"\n📚 {cohort.name}")
        print(f"   Cohort start_date: {cohort.start_date}")
        print(f"   Cohort end_date: {cohort.end_date}")
        print(f"   Première séance: {first_session}")
        print(f"   Dernière séance: {last_session}")
        print(f"   Séances totales: {sessions.count()}")
    else:
        print(f"\n📚 {cohort.name} - AUCUNE SÉANCE")

print("\n" + "=" * 80)
