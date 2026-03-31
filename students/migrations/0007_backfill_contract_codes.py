from django.db import migrations


def backfill_contract_codes(apps, schema_editor):
    Enrollment = apps.get_model('students', 'Enrollment')

    def gen_code(e):
        # replicate logic without model methods
        year = getattr(e.cohort, 'academic_year', None)
        year_label = getattr(year, 'label', '')
        year_code = ''.join(ch for ch in (year_label or '') if ch.isdigit()) or '00000000'
        subj = getattr(e.cohort, 'subject', None)
        subj_name = (getattr(subj, 'name', '') or '').lower()
        if 'jap' in subj_name:
            lang = 'JP'
        elif 'chi' in subj_name:
            lang = 'CH'
        elif 'cor' in subj_name:
            lang = 'KR'
        else:
            base = (getattr(subj, 'name', 'XX') or 'XX').upper()
            lang = (base[:2] if len(base) >= 2 else (base + 'X')[:2])
        modality = getattr(e.cohort, 'modality', 'IN_PERSON')
        is_individual = getattr(e.cohort, 'is_individual', False)
        if is_individual:
            type_code = 'PI' if modality == 'IN_PERSON' else 'OI'
        else:
            type_code = 'P' if modality == 'IN_PERSON' else 'O'
        seq = f"{e.id:05d}" if e.id else "00000"
        return f"{year_code}-{lang}-{type_code}-{seq}"

    for e in Enrollment.objects.select_related('cohort__academic_year', 'cohort__subject').all().order_by('id'):
        if not getattr(e, 'contract_code', None):
            code = gen_code(e)
            # Ensure uniqueness
            existing = Enrollment.objects.filter(contract_code=code).exclude(id=e.id).exists()
            if existing:
                code = f"{code}-{e.id}"
            # direct update avoids calling save hooks unneededly
            Enrollment.objects.filter(id=e.id).update(contract_code=code)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0006_enrollment_contract_code'),
    ]

    operations = [
        migrations.RunPython(backfill_contract_codes, noop),
    ]
