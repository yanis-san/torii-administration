# finance/test_teacher_payroll_by_cohort.py
"""
Tests TDD pour le système de paie des professeurs par cohort.
Système complet et professionnel avec calcul automatique et paiements par cohort.
"""

from django.test import TestCase
from django.urls import reverse
from datetime import date, time, datetime
from core.models import User, AcademicYear, Classroom
from academics.models import Subject, Level, Cohort, WeeklySchedule, CourseSession
from finance.models import TeacherPayment, TeacherCohortPayment
from django.db.models import Sum


class TeacherPayrollByCohortTest(TestCase):
    """Tests pour le système de paie par cohort"""

    def setUp(self):
        """Setup des données de test"""
        print("\n" + "="*70)
        print("SETUP: Création des données de test")
        print("="*70)
        
        # Admin
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        # Professeur
        self.teacher = User.objects.create_user(
            username="prof_yanis",
            password="test123",
            first_name="Yanis",
            last_name="Barbara",
            is_teacher=True,
            birth_date=date(1988, 8, 22)
        )
        
        # Créer le profil prof
        self.teacher_profile = self.teacher.teacher_profile
        self.teacher_profile.payment_frequency = 'MONTHLY'  # Payé mensuellement
        self.teacher_profile.preferred_payment_method = 'CASH'
        self.teacher_profile.save()

        # Année académique
        self.ay = AcademicYear.objects.create(
            label="2024-2025",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            is_current=True
        )

        # Salles de classe
        self.room1 = Classroom.objects.create(name="Salle Japon")
        self.room2 = Classroom.objects.create(name="Salle Corée")

        # Sujets et niveaux
        self.subject_jap = Subject.objects.create(name="Japonais")
        self.subject_kor = Subject.objects.create(name="Coréen")
        self.level_n5 = Level.objects.create(name="JLPT N5")
        self.level_topik2 = Level.objects.create(name="TOPIK 2")

        # Cohort 1 : Japonais N5 - Tarif horaire 1500 DA/h
        self.cohort_jap = Cohort.objects.create(
            name="Japonais N5 - Matin",
            subject=self.subject_jap,
            level=self.level_n5,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            teacher_hourly_rate=1500,
            standard_price=30000,
            schedule_generated=False
        )

        # Cohort 2 : Coréen TOPIK 2 - Tarif horaire 1800 DA/h
        self.cohort_kor = Cohort.objects.create(
            name="Coréen TOPIK 2 - Soir",
            subject=self.subject_kor,
            level=self.level_topik2,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            teacher_hourly_rate=1800,
            standard_price=35000,
            schedule_generated=False
        )

        # Créer les séances pour cohort_jap (2h chacune)
        self.sessions_jap = []
        for i in range(4):
            session = CourseSession.objects.create(
                cohort=self.cohort_jap,
                date=date(2024, 12, 16 + i),
                start_time=time(9, 0),
                end_time=time(11, 0),  # 2 heures
                teacher=self.teacher,
                classroom=self.room1,
                status='SCHEDULED'
            )
            self.sessions_jap.append(session)

        # Créer les séances pour cohort_kor (1.5h chacune)
        self.sessions_kor = []
        for i in range(3):
            session = CourseSession.objects.create(
                cohort=self.cohort_kor,
                date=date(2024, 12, 17 + i),
                start_time=time(18, 0),
                end_time=time(19, 30),  # 1.5 heures
                teacher=self.teacher,
                classroom=self.room2,
                status='SCHEDULED'
            )
            self.sessions_kor.append(session)

        print(f"✓ Admin créé: {self.admin.username}")
        print(f"✓ Prof créé: {self.teacher.get_full_name()}")
        print(f"✓ Cohort 1 créé: {self.cohort_jap.name} ({self.cohort_jap.teacher_hourly_rate} DA/h)")
        print(f"✓ Cohort 2 créé: {self.cohort_kor.name} ({self.cohort_kor.teacher_hourly_rate} DA/h)")
        print(f"✓ 4 séances Japonais + 3 séances Coréen créées")

    def test_01_calculate_earnings_per_cohort(self):
        """Test: Calcul des gains par cohort (séances complétées × tarif horaire)"""
        print("\n" + "-"*70)
        print("TEST 1: Calcul des gains par cohort")
        print("-"*70)

        # Marquer les séances comme COMPLETED
        for session in self.sessions_jap:
            session.status = 'COMPLETED'
            session.save()

        for session in self.sessions_kor:
            session.status = 'COMPLETED'
            session.save()

        # Calcul attendu :
        # Cohort Jap: 4 séances × 2h × 1500 DA/h = 12 000 DA
        # Cohort Kor: 3 séances × 1.5h × 1800 DA/h = 8 100 DA
        # TOTAL: 20 100 DA

        expected_jap = 4 * 2 * 1500
        expected_kor = 3 * 1.5 * 1800
        expected_total = expected_jap + expected_kor

        # Récupérer les séances complétées
        completed_sessions_jap = CourseSession.objects.filter(
            cohort=self.cohort_jap,
            status='COMPLETED'
        )
        
        completed_sessions_kor = CourseSession.objects.filter(
            cohort=self.cohort_kor,
            status='COMPLETED'
        )

        # Calculer les gains
        earnings_jap = 0
        for session in completed_sessions_jap:
            duration = datetime.combine(date.today(), session.end_time) - \
                      datetime.combine(date.today(), session.start_time)
            hours = duration.total_seconds() / 3600
            earnings_jap += hours * session.cohort.teacher_hourly_rate

        earnings_kor = 0
        for session in completed_sessions_kor:
            duration = datetime.combine(date.today(), session.end_time) - \
                      datetime.combine(date.today(), session.start_time)
            hours = duration.total_seconds() / 3600
            earnings_kor += hours * session.cohort.teacher_hourly_rate

        total_earnings = earnings_jap + earnings_kor

        print(f"  Cohort Japonais:")
        print(f"    - Séances: {completed_sessions_jap.count()}")
        print(f"    - Durée totale: 8h (4 × 2h)")
        print(f"    - Tarif: 1500 DA/h")
        print(f"    - Gains: {earnings_jap} DA (attendu: {expected_jap} DA)")

        print(f"  Cohort Coréen:")
        print(f"    - Séances: {completed_sessions_kor.count()}")
        print(f"    - Durée totale: 4.5h (3 × 1.5h)")
        print(f"    - Tarif: 1800 DA/h")
        print(f"    - Gains: {earnings_kor} DA (attendu: {expected_kor} DA)")

        print(f"  TOTAL GAINS: {total_earnings} DA (attendu: {expected_total} DA)")

        self.assertEqual(round(earnings_jap), expected_jap)
        self.assertEqual(round(earnings_kor), expected_kor)
        self.assertEqual(round(total_earnings), expected_total)

        print("✓ Test réussi: Calcul des gains correct")

    def test_02_record_payment_per_cohort(self):
        """Test: Enregistrement d'un paiement pour un cohort spécifique"""
        print("\n" + "-"*70)
        print("TEST 2: Enregistrement d'un paiement par cohort")
        print("-"*70)

        # Marquer les séances Japonais comme COMPLETED
        for session in self.sessions_jap:
            session.status = 'COMPLETED'
            session.save()

        # Calcul du montant dû pour le cohort Japonais
        # 4 séances × 2h × 1500 DA/h = 12 000 DA
        amount_due = 4 * 2 * 1500

        # Enregistrer le paiement
        payment = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_jap,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 31),
            amount_due=amount_due,
            amount_paid=amount_due,
            payment_date=date(2024, 12, 20),
            payment_method='CASH',
            recorded_by=self.admin,
            notes="Paiement pour séances décembre"
        )

        print(f"  Paiement enregistré:")
        print(f"    - Cohort: {payment.cohort.name}")
        print(f"    - Montant dû: {payment.amount_due} DA")
        print(f"    - Montant payé: {payment.amount_paid} DA")
        print(f"    - Reste: {payment.amount_due - payment.amount_paid} DA")
        print(f"    - Date: {payment.payment_date}")

        self.assertEqual(payment.amount_due, amount_due)
        self.assertEqual(payment.amount_paid, amount_due)
        self.assertEqual(payment.amount_due - payment.amount_paid, 0)

        print("✓ Test réussi: Paiement enregistré correctement")

    def test_03_partial_payment_reduces_balance(self):
        """Test: Un paiement partiel réduit correctement le montant dû"""
        print("\n" + "-"*70)
        print("TEST 3: Paiement partiel réduit le montant dû")
        print("-"*70)

        # Marquer les séances Coréen comme COMPLETED
        for session in self.sessions_kor:
            session.status = 'COMPLETED'
            session.save()

        # Montant dû: 3 séances × 1.5h × 1800 DA/h = 8 100 DA
        amount_due = int(3 * 1.5 * 1800)

        # Paiement partiel: seulement 5000 DA
        amount_paid = 5000

        payment = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_kor,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 31),
            amount_due=amount_due,
            amount_paid=amount_paid,
            payment_date=date(2024, 12, 20),
            payment_method='CASH',
            recorded_by=self.admin,
            notes="Paiement partiel"
        )

        balance_remaining = payment.amount_due - payment.amount_paid

        print(f"  Paiement partiel:")
        print(f"    - Montant dû: {payment.amount_due} DA")
        print(f"    - Montant payé: {payment.amount_paid} DA")
        print(f"    - Reste à payer: {balance_remaining} DA")

        self.assertEqual(payment.amount_due, amount_due)
        self.assertEqual(payment.amount_paid, amount_paid)
        self.assertEqual(balance_remaining, amount_due - amount_paid)

        print("✓ Test réussi: Paiement partiel enregistré correctement")

    def test_04_multiple_payments_same_cohort(self):
        """Test: Plusieurs paiements pour le même cohort"""
        print("\n" + "-"*70)
        print("TEST 4: Plusieurs paiements pour le même cohort")
        print("-"*70)

        # Marquer les séances Japonais comme COMPLETED
        for session in self.sessions_jap:
            session.status = 'COMPLETED'
            session.save()

        amount_due = int(4 * 2 * 1500)  # 12 000 DA

        # Premier paiement: 5000 DA
        payment1 = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_jap,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 15),
            amount_due=amount_due,
            amount_paid=5000,
            payment_date=date(2024, 12, 15),
            payment_method='CASH',
            recorded_by=self.admin
        )

        # Deuxième paiement: 7000 DA (solde le compte)
        payment2 = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_jap,
            period_start=date(2024, 12, 16),
            period_end=date(2024, 12, 31),
            amount_due=amount_due,
            amount_paid=7000,
            payment_date=date(2024, 12, 20),
            payment_method='CASH',
            recorded_by=self.admin
        )

        # Total payé
        total_paid = TeacherCohortPayment.objects.filter(
            teacher=self.teacher,
            cohort=self.cohort_jap
        ).aggregate(total=Sum('amount_paid'))['total']

        print(f"  Paiement 1: 5000 DA (date: {payment1.payment_date})")
        print(f"  Paiement 2: 7000 DA (date: {payment2.payment_date})")
        print(f"  Total payé: {total_paid} DA")
        print(f"  Montant dû: {amount_due} DA")
        print(f"  Bilan: {'Soldé ✓' if total_paid >= amount_due else 'Partiel'}")

        self.assertEqual(total_paid, 12000)
        self.assertGreaterEqual(total_paid, amount_due)

        print("✓ Test réussi: Multiples paiements enregistrés correctement")

    def test_05_different_cohorts_independent(self):
        """Test: Les paiements des différents cohorts sont indépendants"""
        print("\n" + "-"*70)
        print("TEST 5: Indépendance des paiements entre cohorts")
        print("-"*70)

        # Marquer toutes les séances comme COMPLETED
        for session in self.sessions_jap + self.sessions_kor:
            session.status = 'COMPLETED'
            session.save()

        amount_jap = int(4 * 2 * 1500)  # 12 000 DA
        amount_kor = int(3 * 1.5 * 1800)  # 8 100 DA

        # Paiement pour Japonais: 10 000 DA
        payment_jap = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_jap,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 31),
            amount_due=amount_jap,
            amount_paid=10000,
            payment_date=date(2024, 12, 20),
            payment_method='CASH',
            recorded_by=self.admin
        )

        # Paiement pour Coréen: 8 100 DA (complet)
        payment_kor = TeacherCohortPayment.objects.create(
            teacher=self.teacher,
            cohort=self.cohort_kor,
            period_start=date(2024, 12, 1),
            period_end=date(2024, 12, 31),
            amount_due=amount_kor,
            amount_paid=amount_kor,
            payment_date=date(2024, 12, 20),
            payment_method='TRANSFER',
            recorded_by=self.admin
        )

        balance_jap = payment_jap.amount_due - payment_jap.amount_paid
        balance_kor = payment_kor.amount_due - payment_kor.amount_paid

        print(f"  Cohort Japonais:")
        print(f"    - Dû: {payment_jap.amount_due} DA")
        print(f"    - Payé: {payment_jap.amount_paid} DA")
        print(f"    - Reste: {balance_jap} DA")

        print(f"  Cohort Coréen:")
        print(f"    - Dû: {payment_kor.amount_due} DA")
        print(f"    - Payé: {payment_kor.amount_paid} DA")
        print(f"    - Reste: {balance_kor} DA")

        self.assertEqual(balance_jap, 2000)  # 12000 - 10000
        self.assertEqual(balance_kor, 0)     # 8100 - 8100

        print("✓ Test réussi: Paiements des cohorts indépendants")

    def test_06_teacher_profile_payment_frequency(self):
        """Test: La fréquence de paiement est stockée dans le profil du prof"""
        print("\n" + "-"*70)
        print("TEST 6: Fréquence de paiement du prof")
        print("-"*70)

        print(f"  Fréquence: {self.teacher_profile.get_payment_frequency_display()}")
        print(f"  Méthode: {self.teacher_profile.get_preferred_payment_method_display()}")

        self.assertEqual(self.teacher_profile.payment_frequency, 'MONTHLY')
        self.assertEqual(self.teacher_profile.preferred_payment_method, 'CASH')

        print("✓ Test réussi: Profil stocke correctement les préférences")
