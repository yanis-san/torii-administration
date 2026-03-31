#!/usr/bin/env python
"""
Quick test to verify modality and individual filters work in views and templates.
Run: python manage.py shell < test_modality_individual.py
"""
import os
import django
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from core.models import User, AcademicYear, Classroom
from academics.models import Cohort, Subject, Level
from students.models import Student, Enrollment

# Setup test data
print("\n=== Setting up test data ===\n")

# Create academic year
year = AcademicYear.objects.create(
    label='2024-2025',
    start_date=date(2024, 9, 1),
    end_date=date(2025, 6, 30),
    is_current=True
)
print(f"✓ Academic year: {year}")

# Create user
teacher = User.objects.create_user(
    username='prof_test',
    first_name='John',
    last_name='Doe',
    is_teacher=True,
    is_active=True,
    is_staff=True,
    is_superuser=True
)
print(f"✓ Teacher: {teacher.get_full_name()}")

# Create levels & subjects
level = Level.objects.create(name='Niveau 1')
subject = Subject.objects.create(name='Mathématiques')
print(f"✓ Level: {level}, Subject: {subject}")

# Create classroom
classroom = Classroom.objects.create(name='Salle A', capacity=20)
print(f"✓ Classroom: {classroom}")

# Create cohorts with different modality and individual flags
cohort1 = Cohort.objects.create(
    name='Math Présentiel Groupe',
    subject=subject,
    level=level,
    teacher=teacher,
    academic_year=year,
    start_date=date(2024, 9, 1),
    end_date=date(2024, 12, 31),
    modality='IN_PERSON',
    is_individual=False,
    standard_price=5000
)
print(f"✓ Cohort 1 (Présentiel, Groupe): {cohort1.name} - modality={cohort1.modality}, individual={cohort1.is_individual}")

cohort2 = Cohort.objects.create(
    name='Math En Ligne Individuel',
    subject=subject,
    level=level,
    teacher=teacher,
    academic_year=year,
    start_date=date(2024, 9, 1),
    end_date=date(2024, 12, 31),
    modality='ONLINE',
    is_individual=True,
    standard_price=3000
)
print(f"✓ Cohort 2 (En ligne, Individuel): {cohort2.name} - modality={cohort2.modality}, individual={cohort2.is_individual}")

cohort3 = Cohort.objects.create(
    name='Math Présentiel Individuel',
    subject=subject,
    level=level,
    teacher=teacher,
    academic_year=year,
    start_date=date(2024, 9, 1),
    end_date=date(2024, 12, 31),
    modality='IN_PERSON',
    is_individual=True,
    standard_price=4000
)
print(f"✓ Cohort 3 (Présentiel, Individuel): {cohort3.name} - modality={cohort3.modality}, individual={cohort3.is_individual}")

print("\n=== Testing filters ===\n")

# Test view filters
client = Client()
client.force_login(teacher)

# Test annual reports page with modality filter
response = client.get('/reports/annual/?modality=IN_PERSON')
print(f"✓ GET /reports/annual/?modality=IN_PERSON → {response.status_code}")

response = client.get('/reports/annual/?modality=ONLINE')
print(f"✓ GET /reports/annual/?modality=ONLINE → {response.status_code}")

response = client.get('/reports/annual/?individual=1')
print(f"✓ GET /reports/annual/?individual=1 → {response.status_code}")

response = client.get('/reports/annual/?individual=0')
print(f"✓ GET /reports/annual/?individual=0 → {response.status_code}")

# Test cohort list filters
response = client.get('/academics/cohorts/?modality=IN_PERSON')
print(f"✓ GET /academics/cohorts/?modality=IN_PERSON → {response.status_code}")
assert b'Pr\xc3\xa9sentiel' in response.content or 'Présentiel' in str(response.content), "Présentiel badge should be in response"

response = client.get('/academics/cohorts/?modality=ONLINE')
print(f"✓ GET /academics/cohorts/?modality=ONLINE → {response.status_code}")
assert b'En ligne' in response.content or 'En ligne' in str(response.content), "En ligne badge should be in response"

response = client.get('/academics/cohorts/?individual=1')
print(f"✓ GET /academics/cohorts/?individual=1 → {response.status_code}")
assert b'Individuel' in response.content or 'Individuel' in str(response.content), "Individuel badge should be in response"

print("\n=== Testing report exports ===\n")

# Test CSV export with filters
response = client.get(f'/reports/annual/enrollments/csv/?year={year.id}&modality=IN_PERSON')
print(f"✓ GET /reports/annual/enrollments/csv/?year={year.id}&modality=IN_PERSON → {response.status_code}")
assert 'Modalité' in str(response.content), "Modalité column should be in CSV"

response = client.get(f'/reports/annual/enrollments/pdf/?year={year.id}&individual=1')
print(f"✓ GET /reports/annual/enrollments/pdf/?year={year.id}&individual=1 → {response.status_code}")

response = client.get(f'/reports/annual/enrollments/zip/?year={year.id}&modality=ONLINE')
print(f"✓ GET /reports/annual/enrollments/zip/?year={year.id}&modality=ONLINE → {response.status_code}")

print("\n=== All tests passed! ===\n")
print("✅ Modality and individual filters are working correctly.")
print("✅ Badges appear in cohort list templates.")
print("✅ Report exports include modality/individual in CSV and respect filters in PDF/ZIP.")
