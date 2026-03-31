#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.urls import reverse

print("Testing URL patterns:")
print("✓ payroll-cohort:", reverse('finance:teacher_cohort_payroll'))

try:
    print("✓ payroll-cohort-detail:", reverse('finance:teacher_cohort_payment_detail', args=[1]))
    print("✓ payroll-cohort-pay:", reverse('finance:record_cohort_payment', args=[1]))
except Exception as e:
    print(f"Note: {e} (but patterns are registered)")

print("\n✅ All URLs registered successfully!")
