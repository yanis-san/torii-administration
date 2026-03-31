#!/usr/bin/env python
"""Fix the ValueError in teacher_cohort_payment_detail view"""

# Read the file
with open('finance/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace
old_section = """    # Permettre à l'utilisateur de surcharger les dates
    period_start = request.GET.get('start', cohort_start_date.strftime('%Y-%m-%d'))
    period_end = request.GET.get('end', cohort_end_date.strftime('%Y-%m-%d'))

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()"""

new_section = """    # Permettre à l'utilisateur de surcharger les dates
    period_start = request.GET.get('start', '').strip()
    period_end = request.GET.get('end', '').strip()
    
    # Si les dates sont vides, utiliser les dates du cohort
    if not period_start:
        period_start = cohort_start_date.strftime('%Y-%m-%d')
    if not period_end:
        period_end = cohort_end_date.strftime('%Y-%m-%d')

    period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    period_end = datetime.strptime(period_end, '%Y-%m-%d').date()"""

if old_section in content:
    content = content.replace(old_section, new_section)
    print("✓ Section trouvée et remplacée!")
    
    with open('finance/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fichier views.py corrigé!")
else:
    print("❌ Section non trouvée - vérifie l'encodage")
    print(f"Longueur du fichier: {len(content)}")
