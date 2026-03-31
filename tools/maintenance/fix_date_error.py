#!/usr/bin/env python
"""Fix the ValueError in teacher_cohort_payment_detail view"""

# Read the file
with open('c:\\Users\\Social Media Manager\\Documents\\codes\\school_management\\finance\\views.py', 'r') as f:
    content = f.read()

# Find and replace the problematic code
old_code = '''    # Permettre à l'utilisateur de surcharger les dates
    period_start = request.GET.get('start', cohort_start_date.strftime('%Y-%m-%d'))
    period_end = request.GET.get('end', cohort_end_date.strftime('%Y-%m-%d'))

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()'''

new_code = '''    # Permettre à l'utilisateur de surcharger les dates
    period_start = request.GET.get('start', '').strip()
    period_end = request.GET.get('end', '').strip()
    
    # Si les dates sont vides, utiliser les dates du cohort
    if not period_start:
        period_start = cohort_start_date.strftime('%Y-%m-%d')
    if not period_end:
        period_end = cohort_end_date.strftime('%Y-%m-%d')

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ Code corrigé!")
else:
    print("❌ Code non trouvé")

# Write back
with open('c:\\Users\\Social Media Manager\\Documents\\codes\\school_management\\finance\\views.py', 'w') as f:
    f.write(content)

print("✅ Fichier mis à jour!")
