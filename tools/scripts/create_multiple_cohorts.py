#!/usr/bin/env python
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from academics.models import CourseSession, Cohort, Level, Subject, AcademicYear
from core.models import User, TeacherProfile
from django.contrib.auth.models import Group

print("=" * 80)
print("CRÉATION DE DONNÉES DE TEST AVEC PLUSIEURS COHORTS")
print("=" * 80)

# Récupérer ou créer le prof
teacher = User.objects.filter(is_teacher=True).first()
if not teacher:
    print("❌ Aucun professeur trouvé!")
    exit(1)

print(f"\n✓ Professeur: {teacher.get_full_name()}")

# Ajouter le profil teacherprofile s'il n'existe pas
profile, created = TeacherProfile.objects.get_or_create(
    user=teacher,
    defaults={
        'payment_frequency': 'MONTHLY',
        'preferred_payment_method': 'CASH'
    }
)
if created:
    print(f"✓ Profil teacher créé")
else:
    print(f"✓ Profil teacher existe déjà: {profile.get_payment_frequency_display()}")

# Récupérer l'academic year existante
academic_year = AcademicYear.objects.first()
if not academic_year:
    academic_year = AcademicYear.objects.create(name='2026')
    print(f"✓ Academic year créée: {academic_year}")
else:
    print(f"✓ Academic year: {academic_year}")

# Créer 3 cohorts différents
cohort_data = [
    {
        'name': 'Japonais N5 - Matin',
        'start': datetime(2025, 12, 1),
        'end': datetime(2026, 2, 28),
        'rate': 1500,
        'sessions_count': 8,
    },
    {
        'name': 'Coréen TOPIK 2 - Soir',
        'start': datetime(2025, 12, 8),
        'end': datetime(2026, 3, 15),
        'rate': 1800,
        'sessions_count': 6,
    },
    {
        'name': 'Chinois HSK 3 - Week-end',
        'start': datetime(2025, 12, 6),
        'end': datetime(2026, 3, 1),
        'rate': 2000,
        'sessions_count': 5,
    },
]

for cohort_info in cohort_data:
    # Récupérer ou créer le level et subject
    level, _ = Level.objects.get_or_create(name='N1')
    subject_name = cohort_info['name'].split()[0]  # Prendre le premier mot (Japonais, Coréen, Chinois)
    subject, _ = Subject.objects.get_or_create(name=subject_name)
    
    # Créer ou récupérer le cohort
    cohort, created = Cohort.objects.get_or_create(
        name=cohort_info['name'],
        defaults={
            'subject': subject,
            'level': level,
            'academic_year': academic_year,
            'teacher': teacher,
            'start_date': cohort_info['start'].date(),
            'end_date': cohort_info['end'].date(),
            'teacher_hourly_rate': cohort_info['rate'],
            'standard_price': 15000,  # Prix forfaitaire par élève
        }
    )
    
    if created:
        print(f"\n✓ Cohort créé: {cohort.name} ({cohort_info['rate']} DA/h)")
    else:
        print(f"\n✓ Cohort existe: {cohort.name}")
    
    # Créer les séances
    existing_sessions = CourseSession.objects.filter(cohort=cohort).count()
    if existing_sessions == 0:
        from academics.models import Classroom
        # Récupérer une salle
        classroom = Classroom.objects.first()
        if not classroom:
            classroom = Classroom.objects.create(name='Salle 1', capacity=20)
        
        current_date = cohort_info['start']
        for i in range(cohort_info['sessions_count']):
            # Créer une session par semaine, 2h par session
            session = CourseSession.objects.create(
                cohort=cohort,
                date=current_date.date(),
                start_time=datetime.strptime('10:00', '%H:%M').time(),
                end_time=datetime.strptime('12:00', '%H:%M').time(),
                teacher=teacher,
                classroom=classroom,
                status='COMPLETED',
                note=f'Séance {i+1}',
            )
            print(f"  • Séance {i+1}: {current_date.date()} (2h) - Status: COMPLETED")
            current_date += timedelta(days=7)  # Une séance par semaine
    else:
        print(f"  Déjà {existing_sessions} séances existantes")

print("\n" + "=" * 80)
print("✅ DONNÉES DE TEST CRÉÉES!")
print("=" * 80)
