#!/usr/bin/env python
"""
Script pour exécuter les tests TDD du système de paie des profs
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Imports après setup
from finance.test_teacher_payroll_by_cohort import TeacherPayrollByCohortTest
import unittest

if __name__ == '__main__':
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TeacherPayrollByCohortTest)
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit code
    sys.exit(0 if result.wasSuccessful() else 1)
