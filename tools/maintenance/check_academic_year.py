#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from academics.models import Cohort, AcademicYear

# Voir un cohort existant
existing = Cohort.objects.first()
if existing:
    print(f"Cohort existant:")
    print(f"  - name: {existing.name}")
    print(f"  - academic_year: {existing.academic_year}")
    print(f"  - subject: {existing.subject}")
    print(f"  - level: {existing.level}")

# Voir les academic years disponibles
years = AcademicYear.objects.all()
if years:
    print(f"\nAcademic Years disponibles:")
    for year in years:
        print(f"  - {year}")
else:
    print("\nAucune academic year! On doit en créer une.")
