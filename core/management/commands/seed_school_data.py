"""
Management command pour générer des données de test pour une école de langues asiatiques
Usage: python manage.py seed_school_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
import random
import string

from core.models import User, AcademicYear, Classroom
from academics.models import Subject, Level, Cohort, WeeklySchedule, CourseSession
from students.models import Student, Enrollment, Attendance
from finance.models import Tariff, Payment


class Command(BaseCommand):
    help = 'Génère des données de test complètes pour une école de langues asiatiques'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprimer toutes les données existantes avant de générer',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('[!] Suppression des donnees existantes...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('[*] Generation des donnees de test...'))

        # 1. Année académique
        self.stdout.write('[1/12] Creation de l\'annee academique...')
        self.academic_year = self.create_academic_year()

        # 2. Salles de classe
        self.stdout.write('[2/12] Creation des salles de classe...')
        self.classrooms = self.create_classrooms()

        # 3. Matières et niveaux
        self.stdout.write('[3/12] Creation des matieres et niveaux...')
        self.subjects = self.create_subjects()
        self.levels = self.create_levels()

        # 4. Professeurs
        self.stdout.write('[4/12] Creation des professeurs...')
        self.teachers = self.create_teachers()

        # 5. Tarifs
        self.stdout.write('[5/12] Creation des tarifs...')
        self.tariffs = self.create_tariffs()

        # 6. Étudiants
        self.stdout.write('[6/12] Creation des etudiants...')
        self.students = self.create_students(60)

        # 7. Groupes (Cohorts)
        self.stdout.write('[7/12] Creation des groupes de cours...')
        self.cohorts = self.create_cohorts()

        # 8. Créneaux hebdomadaires
        self.stdout.write('[8/12] Creation des creneaux hebdomadaires...')
        self.create_weekly_schedules()

        # 9. Génération des séances
        self.stdout.write('[9/12] Generation des seances de cours...')
        self.generate_sessions()

        # 10. Inscriptions
        self.stdout.write('[10/12] Inscription des etudiants...')
        self.enrollments = self.create_enrollments()

        # 11. Présences
        self.stdout.write('[11/12] Generation des presences...')
        self.mark_attendances()

        # 12. Paiements
        self.stdout.write('[12/12] Generation des paiements...')
        self.create_payments()

        # Statistiques finales
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('*** GENERATION TERMINEE ***'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.print_statistics()

    def clear_data(self):
        """Supprime toutes les données existantes"""
        Payment.objects.all().delete()
        Attendance.objects.all().delete()
        Enrollment.objects.all().delete()
        CourseSession.objects.all().delete()
        WeeklySchedule.objects.all().delete()
        Cohort.objects.all().delete()
        Student.objects.all().delete()
        Tariff.objects.all().delete()
        Level.objects.all().delete()
        Subject.objects.all().delete()
        Classroom.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        AcademicYear.objects.all().delete()

    def create_academic_year(self):
        """Crée l'année académique 2024-2025"""
        ay, created = AcademicYear.objects.get_or_create(
            label="2024-2025",
            defaults={
                'start_date': date(2024, 9, 1),
                'end_date': date(2025, 6, 30)
            }
        )
        self.stdout.write(f'   > Annee academique: {ay.label}')
        return ay

    def create_classrooms(self):
        """Crée les salles de classe"""
        classrooms_data = [
            'Salle 101', 'Salle 102', 'Salle 103',
            'Labo Multimédia', 'Salle Visio',
            'Espace Conversation', 'Bibliothèque'
        ]
        classrooms = []
        for name in classrooms_data:
            classroom, created = Classroom.objects.get_or_create(name=name)
            classrooms.append(classroom)

        # Ajouter une "salle" virtuelle pour les cours en ligne
        online, _ = Classroom.objects.get_or_create(name='En Ligne (Zoom)')
        classrooms.append(online)

        self.stdout.write(f'   > {len(classrooms)} salles creees')
        return classrooms

    def create_subjects(self):
        """Crée les matières (langues asiatiques)"""
        subjects_data = ['Japonais', 'Chinois (Mandarin)', 'Coreen']
        subjects = {}
        for name in subjects_data:
            subject, created = Subject.objects.get_or_create(name=name)
            subjects[name] = subject

        self.stdout.write(f'   > {len(subjects)} matieres creees')
        return subjects

    def create_levels(self):
        """Crée les niveaux pour chaque langue"""
        levels_data = {
            'Japonais': ['Debutant (A1)', 'Elementaire (A2)', 'JLPT N5', 'JLPT N4',
                        'JLPT N3', 'JLPT N2', 'JLPT N1'],
            'Chinois (Mandarin)': ['Debutant (A1)', 'Elementaire (A2)', 'HSK 1',
                                  'HSK 2', 'HSK 3', 'HSK 4', 'HSK 5', 'HSK 6'],
            'Coreen': ['Debutant (A1)', 'Elementaire (A2)', 'TOPIK I (1-2)',
                      'TOPIK II (3-4)', 'TOPIK II (5-6)'],
        }

        levels = {}
        count = 0
        for subject_name, level_names in levels_data.items():
            levels[subject_name] = []
            for level_name in level_names:
                level, created = Level.objects.get_or_create(name=level_name)
                levels[subject_name].append(level)
                count += 1

        self.stdout.write(f'   > {count} niveaux crees')
        return levels

    def create_teachers(self):
        """Crée les professeurs"""
        teachers_data = [
            ('tanaka', 'Yuki', 'Tanaka', 2000, True),
            ('wang', 'Li', 'Wang', 1800, True),
            ('kim', 'Min-Jun', 'Kim', 1900, True),
            ('sato', 'Haruka', 'Sato', 2100, True),
            ('chen', 'Wei', 'Chen', 1850, True),
            ('park', 'Ji-Woo', 'Park', 1950, True),
        ]

        teachers = []
        for username, first_name, last_name, rate, is_teacher in teachers_data:
            teacher, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{username}@ecole-asie.fr',
                    'is_teacher': is_teacher,
                    'birth_date': date(1985, 1, 1) + timedelta(days=random.randint(0, 3650)),
                }
            )
            if created:
                teacher.set_password('password123')
                teacher.save()
            teachers.append(teacher)

        self.stdout.write(f'   > {len(teachers)} professeurs crees')
        return teachers

    def create_tariffs(self):
        """Crée les tarifs"""
        tariffs_data = [
            ('Standard Groupe', 8000),
            ('Tarif Reduit Etudiant', 6500),
            ('Tarif Premium', 10000),
            ('Pack 10h Individuel', 15000),
            ('Pack 20h Individuel', 28000),
            ('Cours en Ligne', 7000),
        ]

        tariffs = {}
        for name, amount in tariffs_data:
            tariff, created = Tariff.objects.get_or_create(
                name=name,
                defaults={'amount': amount}
            )
            tariffs[name] = tariff

        self.stdout.write(f'   > {len(tariffs)} tarifs crees')
        return tariffs

    def create_students(self, count=60):
        """Crée des étudiants avec des données réalistes"""
        first_names = [
            'Emma', 'Louis', 'Chloé', 'Lucas', 'Léa', 'Arthur', 'Manon', 'Hugo',
            'Camille', 'Nathan', 'Inès', 'Tom', 'Sarah', 'Théo', 'Jade', 'Antoine',
            'Marie', 'Paul', 'Clara', 'Gabriel', 'Zoé', 'Jules', 'Lily', 'Adam',
            'Lina', 'Raphaël', 'Nina', 'Mathis', 'Alice', 'Maxime', 'Rose', 'Alexandre',
            'Mila', 'Enzo', 'Léna', 'Noah', 'Anna', 'Ethan', 'Sofia', 'Mathéo',
            'Juliette', 'Maël', 'Eva', 'Timéo', 'Louise', 'Nolan', 'Ambre', 'Yanis',
            'Anaïs', 'Benjamin', 'Victoria', 'Samuel', 'Julia', 'Robin', 'Charlotte',
            'Gabin', 'Margaux', 'Pierre', 'Océane', 'Thomas'
        ]

        last_names = [
            'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit',
            'Durand', 'Leroy', 'Moreau', 'Simon', 'Laurent', 'Lefebvre', 'Michel',
            'Garcia', 'David', 'Bertrand', 'Roux', 'Vincent', 'Fournier', 'Morel',
            'Girard', 'André', 'Lefevre', 'Mercier', 'Dupont', 'Lambert', 'Bonnet',
            'François', 'Martinez', 'Legrand', 'Garnier', 'Faure', 'Rousseau', 'Blanc',
            'Guerin', 'Muller', 'Henry', 'Roussel', 'Nicolas', 'Perrin', 'Morin',
            'Mathieu', 'Clement', 'Gauthier', 'Dumont', 'Lopez', 'Fontaine', 'Chevalier',
            'Robin', 'Masson', 'Sanchez', 'Gerard', 'Nguyen', 'Boyer', 'Denis',
            'Lemaire', 'Duval', 'Joly', 'Gautier'
        ]

        students = []
        used_codes = set()

        for i in range(count):
            # Générer un code étudiant unique
            while True:
                code = f"ETU-2024-{random.randint(1000, 9999)}"
                if code not in used_codes:
                    used_codes.add(code)
                    break

            first_name = random.choice(first_names)
            last_name = random.choice(last_names)

            # Email basé sur le nom
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}@email.fr"

            # Téléphone français
            phone = f"0{random.randint(6, 7)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}"

            # Date de naissance (entre 16 et 50 ans)
            age_days = random.randint(16*365, 50*365)
            birth_date = date.today() - timedelta(days=age_days)

            student, created = Student.objects.get_or_create(
                student_code=code,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                    'phone_2': '',
                    'birth_date': birth_date,
                }
            )
            students.append(student)

        self.stdout.write(f'   > {len(students)} etudiants crees')
        return students

    def create_cohorts(self):
        """Crée les groupes de cours (en ligne, présentiel, individuel)"""
        cohorts = []

        # Configuration des groupes
        cohorts_config = [
            # Japonais
            ('Japonais', 'Debutant (A1)', 'Groupe Debutant Presentiel', 'presentiel', 1800, self.teachers[0]),
            ('Japonais', 'JLPT N5', 'Groupe N5 En Ligne', 'en_ligne', 1600, self.teachers[0]),
            ('Japonais', 'JLPT N3', 'Groupe N3 Presentiel', 'presentiel', 2000, self.teachers[3]),

            # Chinois
            ('Chinois (Mandarin)', 'Debutant (A1)', 'Groupe Debutant Presentiel', 'presentiel', 1800, self.teachers[1]),
            ('Chinois (Mandarin)', 'HSK 2', 'Groupe HSK2 En Ligne', 'en_ligne', 1700, self.teachers[1]),
            ('Chinois (Mandarin)', 'HSK 4', 'Groupe HSK4 Presentiel', 'presentiel', 2100, self.teachers[4]),

            # Coreen
            ('Coreen', 'Debutant (A1)', 'Groupe Debutant Presentiel', 'presentiel', 1900, self.teachers[2]),
            ('Coreen', 'TOPIK I (1-2)', 'Groupe TOPIK I En Ligne', 'en_ligne', 1700, self.teachers[2]),
            ('Coreen', 'TOPIK II (3-4)', 'Groupe TOPIK II Presentiel', 'presentiel', 2000, self.teachers[5]),
        ]

        # Créer les cours individuels
        individual_config = [
            ('Japonais', 'JLPT N2', 'Cours Individuel Japonais', self.teachers[3]),
            ('Chinois (Mandarin)', 'HSK 5', 'Cours Individuel Chinois', self.teachers[4]),
            ('Coreen', 'TOPIK II (5-6)', 'Cours Individuel Coreen', self.teachers[5]),
        ]

        # Créer les groupes standards
        for subject_name, level_name, cohort_name, mode, rate, teacher in cohorts_config:
            subject = self.subjects[subject_name]
            level = next((l for l in self.levels[subject_name] if l.name == level_name), self.levels[subject_name][0])

            cohort, created = Cohort.objects.get_or_create(
                name=f"{subject.name} - {cohort_name}",
                defaults={
                    'subject': subject,
                    'level': level,
                    'teacher': teacher,
                    'academic_year': self.academic_year,
                    'start_date': date(2024, 9, 15),
                    'end_date': date(2025, 6, 15),
                    'teacher_hourly_rate': rate,
                    'standard_price': 8000,
                }
            )
            cohorts.append(cohort)

        # Créer les cours individuels
        for subject_name, level_name, cohort_name, teacher in individual_config:
            subject = self.subjects[subject_name]
            level = next((l for l in self.levels[subject_name] if l.name == level_name), self.levels[subject_name][0])

            cohort, created = Cohort.objects.get_or_create(
                name=f"{subject.name} - {cohort_name}",
                defaults={
                    'subject': subject,
                    'level': level,
                    'teacher': teacher,
                    'academic_year': self.academic_year,
                    'start_date': date(2024, 9, 15),
                    'end_date': date(2025, 6, 15),
                    'teacher_hourly_rate': rate * 1.5,  # Tarif plus élevé pour individuel
                    'standard_price': 15000,
                }
            )
            cohorts.append(cohort)

        self.stdout.write(f'   > {len(cohorts)} groupes crees')
        return cohorts

    def create_weekly_schedules(self):
        """Crée les créneaux hebdomadaires pour chaque groupe"""
        schedules_config = [
            # Index cohort, jour (0=lundi), heure début, heure fin, salle
            (0, 1, time(18, 0), time(20, 0), 0),  # Japonais Débutant Présentiel: Mardi 18h-20h
            (1, 3, time(19, 0), time(21, 0), 4),  # Japonais N5 En Ligne: Jeudi 19h-21h
            (2, 5, time(14, 0), time(16, 30), 1), # Japonais N3 Présentiel: Samedi 14h-16h30

            (3, 2, time(18, 30), time(20, 30), 0), # Chinois Débutant Présentiel: Mercredi 18h30-20h30
            (4, 4, time(19, 0), time(21, 0), 4),   # Chinois HSK2 En Ligne: Vendredi 19h-21h
            (5, 5, time(10, 0), time(12, 30), 2),  # Chinois HSK4 Présentiel: Samedi 10h-12h30

            (6, 1, time(18, 30), time(20, 30), 2), # Coréen Débutant Présentiel: Mardi 18h30-20h30
            (7, 3, time(19, 30), time(21, 30), 4), # Coréen TOPIK I En Ligne: Jeudi 19h30-21h30
            (8, 5, time(14, 0), time(16, 30), 3),  # Coréen TOPIK II Présentiel: Samedi 14h-16h30
        ]

        count = 0
        for cohort_idx, day, start_time, end_time, classroom_idx in schedules_config:
            cohort = self.cohorts[cohort_idx]
            classroom = self.classrooms[classroom_idx]

            schedule, created = WeeklySchedule.objects.get_or_create(
                cohort=cohort,
                day_of_week=day,
                defaults={
                    'start_time': start_time,
                    'end_time': end_time,
                    'classroom': classroom,
                }
            )
            count += 1

        # Créneaux pour cours individuels (flexibles)
        for i in range(9, 12):
            cohort = self.cohorts[i]
            # Cours individuels le samedi matin
            schedule, created = WeeklySchedule.objects.get_or_create(
                cohort=cohort,
                day_of_week=5,  # Samedi
                defaults={
                    'start_time': time(9 + (i-9), 0),
                    'end_time': time(10 + (i-9), 30),
                    'classroom': self.classrooms[5],  # Espace Conversation
                }
            )
            count += 1

        self.stdout.write(f'   > {count} creneaux hebdomadaires crees')

    def generate_sessions(self):
        """Génère les séances de cours à partir des créneaux"""
        count = 0
        for cohort in self.cohorts:
            # Marquer comme généré
            cohort.schedule_generated = True
            cohort.save()

            # Générer les séances à partir des créneaux
            schedules = WeeklySchedule.objects.filter(cohort=cohort)

            if not schedules.exists():
                continue

            # Générer des séances depuis septembre jusqu'à aujourd'hui + 2 semaines
            start_date = date(2024, 9, 15)
            end_date = date.today() + timedelta(weeks=2)

            current_date = start_date
            while current_date <= end_date:
                for schedule in schedules:
                    # Calculer la date de la séance
                    days_until = (schedule.day_of_week - current_date.weekday()) % 7
                    session_date = current_date + timedelta(days=days_until)

                    if session_date < start_date or session_date > end_date:
                        continue

                    # Déterminer le statut
                    if session_date < date.today() - timedelta(days=7):
                        status = 'COMPLETED'
                    elif session_date < date.today():
                        status = random.choice(['COMPLETED', 'COMPLETED', 'SCHEDULED'])
                    else:
                        status = 'SCHEDULED'

                    # Créer la séance
                    session, created = CourseSession.objects.get_or_create(
                        cohort=cohort,
                        date=session_date,
                        start_time=schedule.start_time,
                        defaults={
                            'end_time': schedule.end_time,
                            'status': status,
                            'teacher': cohort.teacher,
                            'classroom': schedule.classroom,
                        }
                    )

                    if created:
                        count += 1

                current_date += timedelta(weeks=1)

        self.stdout.write(f'   > {count} seances generees')

    def create_enrollments(self):
        """Inscrit les étudiants dans les groupes"""
        enrollments = []

        # Répartir les étudiants
        students_per_group = {
            0: 12,  # Japonais Débutant Présentiel
            1: 15,  # Japonais N5 En Ligne
            2: 8,   # Japonais N3 Présentiel
            3: 14,  # Chinois Débutant Présentiel
            4: 16,  # Chinois HSK2 En Ligne
            5: 9,   # Chinois HSK4 Présentiel
            6: 13,  # Coréen Débutant Présentiel
            7: 12,  # Coréen TOPIK I En Ligne
            8: 7,   # Coréen TOPIK II Présentiel
            9: 2,   # Cours Individuel Japonais
            10: 2,  # Cours Individuel Chinois
            11: 2,  # Cours Individuel Coréen
        }

        student_pool = list(self.students)
        random.shuffle(student_pool)

        current_idx = 0
        for cohort_idx, num_students in students_per_group.items():
            cohort = self.cohorts[cohort_idx]

            for i in range(num_students):
                if current_idx >= len(student_pool):
                    break

                student = student_pool[current_idx]
                current_idx += 1

                # Déterminer le tarif et le plan de paiement
                if 'Individuel' in cohort.name:
                    tariff = self.tariffs['Pack 10h Individuel']
                    payment_plan = 'PACK'
                    hours_purchased = 10
                elif 'En Ligne' in cohort.name:
                    tariff = self.tariffs['Cours en Ligne']
                    payment_plan = random.choice(['FULL', 'MONTHLY'])
                    hours_purchased = 0
                else:
                    tariff = random.choice([
                        self.tariffs['Standard Groupe'],
                        self.tariffs['Tarif Reduit Etudiant'],
                    ])
                    payment_plan = random.choice(['FULL', 'FULL', 'MONTHLY', 'PACK'])
                    hours_purchased = 20 if payment_plan == 'PACK' else 0

                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    cohort=cohort,
                    defaults={
                        'tariff': tariff,
                        'payment_plan': payment_plan,
                        'hours_purchased': hours_purchased,
                        'is_active': True,
                    }
                )

                if created:
                    enrollments.append(enrollment)

        self.stdout.write(f'   > {len(enrollments)} inscriptions creees')
        return enrollments

    def mark_attendances(self):
        """Marque les présences pour les séances passées"""
        count = 0

        # Récupérer toutes les séances terminées
        completed_sessions = CourseSession.objects.filter(status='COMPLETED')

        for session in completed_sessions:
            attendances = Attendance.objects.filter(session=session)

            for attendance in attendances:
                # 85% de présence, 10% d'absence, 5% de retard
                rand = random.random()
                if rand < 0.85:
                    attendance.status = 'PRESENT'
                    attendance.billable = True
                elif rand < 0.95:
                    attendance.status = 'ABSENT'
                    attendance.billable = True  # Absence facturée
                else:
                    attendance.status = 'LATE'
                    attendance.billable = True

                attendance.save()
                count += 1

        self.stdout.write(f'   > {count} presences marquees')

    def create_payments(self):
        """Génère les paiements pour les inscriptions"""
        count = 0
        payment_methods = ['CASH', 'CARD', 'TRANSFER', 'CHECK']

        for enrollment in self.enrollments:
            # Montant total à payer (déjà un entier)
            total_amount = enrollment.tariff.amount

            # Décider combien payer
            if enrollment.payment_plan == 'FULL':
                # Paiement complet (80% payent tout, 20% payent partiellement)
                if random.random() < 0.8:
                    amount_paid = total_amount
                else:
                    amount_paid = int(total_amount * random.uniform(0.3, 0.8))
            else:
                # Paiement mensuel ou pack
                amount_paid = int(total_amount * random.uniform(0.4, 0.9))

            # Créer 1 à 3 paiements
            num_payments = random.randint(1, min(3, int(amount_paid / 2000) + 1))

            payments_made = 0
            for i in range(num_payments):
                if i == num_payments - 1:
                    # Dernier paiement = le reste (en entier)
                    payment_amount = amount_paid - payments_made
                else:
                    # Paiement intermédiaire (arrondi à l'entier)
                    payment_amount = int(amount_paid / num_payments)
                    payments_made += payment_amount

                payment = Payment.objects.create(
                    enrollment=enrollment,
                    amount=payment_amount,
                    method=random.choice(payment_methods),
                    recorded_by=enrollment.cohort.teacher,
                )
                # Modifier la date de création pour simuler un paiement dans le passé
                payment.created_at = date(2024, 9, 15) + timedelta(days=random.randint(0, 90))
                payment.save()
                count += 1

        self.stdout.write(f'   > {count} paiements crees')

    def print_statistics(self):
        """Affiche les statistiques finales"""
        self.stdout.write(f'\n== STATISTIQUES ==')
        self.stdout.write(f'   - Matieres: {Subject.objects.count()}')
        self.stdout.write(f'   - Niveaux: {Level.objects.count()}')
        self.stdout.write(f'   - Professeurs: {User.objects.filter(is_teacher=True).count()}')
        self.stdout.write(f'   - Etudiants: {Student.objects.count()}')
        self.stdout.write(f'   - Groupes: {Cohort.objects.count()}')
        self.stdout.write(f'   - Inscriptions: {Enrollment.objects.count()}')
        self.stdout.write(f'   - Seances: {CourseSession.objects.count()}')
        self.stdout.write(f'   - Presences: {Attendance.objects.count()}')
        self.stdout.write(f'   - Paiements: {Payment.objects.count()}')

        # Statistiques financières
        total_payments = sum(p.amount for p in Payment.objects.all())
        total_due = sum(e.tariff.amount for e in Enrollment.objects.all())

        self.stdout.write(f'\n== FINANCES ==')
        self.stdout.write(f'   - Chiffre d\'affaires attendu: {total_due:,} DA'.replace(',', ' '))
        self.stdout.write(f'   - Montant encaisse: {total_payments:,} DA'.replace(',', ' '))
        self.stdout.write(f'   - Taux de recouvrement: {(total_payments/total_due*100) if total_due > 0 else 0:.1f}%')

        self.stdout.write(f'\n== ETUDIANTS PAR LANGUE ==')
        for subject in Subject.objects.all():
            count = Enrollment.objects.filter(cohort__subject=subject).count()
            self.stdout.write(f'   - {subject.name}: {count} etudiants')

        self.stdout.write(f'\n== TAUX DE PRESENCE ==')
        total_att = Attendance.objects.filter(session__status='COMPLETED').count()
        present = Attendance.objects.filter(session__status='COMPLETED', status='PRESENT').count()
        if total_att > 0:
            self.stdout.write(f'   - {present}/{total_att} presences ({present/total_att*100:.1f}%)')
