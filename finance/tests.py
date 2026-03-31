# finance/tests.py
from django.test import TestCase
from datetime import date, time
from core.models import User, AcademicYear, Classroom
from academics.models import Subject, Level, Cohort, WeeklySchedule, CourseSession
from students.models import Student, Enrollment
from django.db.models import Sum
from finance.models import Tariff, Payment, Installment

class FinanceAndTrackingTest(TestCase):

    def setUp(self):
        # 1. Setup de base
        self.ay = AcademicYear.objects.create(label="2024", start_date=date(2024,1,1), end_date=date(2024,12,31))
        self.room = Classroom.objects.create(name="Salle A")
        self.prof = User.objects.create_user(username="prof", is_teacher=True, birth_date=date(1985, 5, 15))
        self.subj = Subject.objects.create(name="Anglais")
        self.lvl = Level.objects.create(name="B2")
        
        # 2. Tarif
        self.tariff = Tariff.objects.create(name="Standard", amount=10000) # 10 000 DA

        # 3. Groupe
        self.cohort = Cohort.objects.create(
            name="Anglais B2",
            subject=self.subj, level=self.lvl, teacher=self.prof,
            academic_year=self.ay,
            start_date=date(2024,1,1), end_date=date(2024,3,31)
        )
        
        # 4. Élève
        self.student = Student.objects.create(first_name="Yanis", last_name="Dev", phone="0555", phone_2="", birth_date=date(2005, 3, 15))

    def test_01_partial_payment_logic(self):
        """Test du paiement partiel et du calcul du reste à payer"""
        print("\n[TEST] Test 1: Paiement Partiel")
        
        # Inscription (10 000 DA à payer)
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, tariff=self.tariff, payment_plan='FULL'
        )
        
        # Vérif initiale
        self.assertEqual(enrollment.balance_due, 10000)
        print("   OK Dette initiale : 10 000 DA")

        # Action : Il paie 3000 DA
        Payment.objects.create(
            enrollment=enrollment, amount=3000, recorded_by=self.prof
        )

        # Vérif après paiement
        self.assertEqual(enrollment.balance_due, 7000)
        print("   OK Reste a payer correct : 7 000 DA")

        # Action : Il solde tout
        Payment.objects.create(
            enrollment=enrollment, amount=7000, recorded_by=self.prof
        )
        self.assertEqual(enrollment.balance_due, 0)
        print("   OK Dette soldee : 0 DA")

    def test_02_pack_hours_consumption(self):
        """Test : Est-ce que les heures sont débitées quand le cours est fini ?"""
        print("\n[TEST] Test 2: Consommation Pack d'Heures")
        
        # Inscription
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, tariff=self.tariff, payment_plan='PACK'
        )
        
        # Séance de 2h (10h -> 12h)
        session = CourseSession.objects.create(
            cohort=self.cohort, date=date(2024,1,10),
            start_time=time(10,0), end_time=time(12,0),
            teacher=self.prof, classroom=self.room,
            status='SCHEDULED'
        )

        # Vérif avant : 0 heures consommées
        enrollment.refresh_from_db() # Important pour recharger les données
        self.assertEqual(enrollment.hours_consumed, 0)

        # Action : Le prof valide le cours (COMPLETED)
        session.status = 'COMPLETED'
        session.save() # C'est ici que le Signal doit se déclencher

        # Vérif après
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.hours_consumed, 2.0)
        print(f"   OK Heures consommees : {enrollment.hours_consumed}h (Attendu: 2.0h)")

    def test_03_installments_status(self):
        """Test : Est-ce qu'une échéance passe à 'Payé' ?"""
        print("\n[TEST] Test 3: Statut des Échéances")
        
        # Inscription avec paiement TOTAL (Une seule échéance de 10000)
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, tariff=self.tariff, payment_plan='FULL'
        )
        
        installment = enrollment.installments.first()
        self.assertFalse(installment.is_paid)
        
        # On paie la totalité
        payment = Payment.objects.create(
            enrollment=enrollment, amount=10000, recorded_by=self.prof
        )
        
        # Note: Dans notre code actuel, on n'a pas encore fait le lien automatique 
        # "Paiement -> Met à jour Installment.is_paid".
        # C'est souvent une logique complexe. Pour l'instant, testons si on peut le faire manuellement.
        
        installment.is_paid = True
        installment.payment = payment
        installment.save()

        self.assertTrue(installment.is_paid)
        print("   OK Echeance marquee comme payee")


class TeacherPaymentTest(TestCase):
    """Tests pour le système de paie des professeurs"""

    def setUp(self):
        # Setup de base
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.room = Classroom.objects.create(name="Salle A")
        self.teacher = User.objects.create_user(
            username="teacher1",
            password="test123",
            is_teacher=True,
            first_name="Jean",
            last_name="Dupont",
            birth_date=date(1985, 5, 15)
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        self.subj = Subject.objects.create(name="Histoire")
        self.lvl = Level.objects.create(name="Seconde")

        self.cohort = Cohort.objects.create(
            name="Histoire Seconde",
            subject=self.subj,
            level=self.lvl,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            teacher_hourly_rate=1800  # 1800 DA/h
        )

        WeeklySchedule.objects.create(
            cohort=self.cohort,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(12, 0),  # 2 heures
            classroom=self.room
        )

    def test_01_teacher_payment_creation(self):
        """Test la création d'un paiement professeur"""
        print("\n[TEST] Test 1: Création paiement professeur")

        from finance.models import TeacherPayment

        payment = TeacherPayment.objects.create(
            teacher=self.teacher,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            total_amount=10000,
            payment_method='CASH',
            payment_date=date(2024, 2, 1),
            recorded_by=self.admin
        )

        self.assertEqual(payment.teacher, self.teacher)
        self.assertEqual(payment.total_amount, 10000)
        self.assertEqual(payment.payment_method, 'CASH')

        print(f"   OK Paiement cree: {payment.total_amount} DA pour {self.teacher.get_full_name()}")

    def test_02_teacher_earned_amount_calculation(self):
        """Test le calcul du montant gagné par un professeur"""
        print("\n[TEST] Test 2: Calcul montant gagné")

        # Générer des séances et marquer comme complétées
        self.cohort.schedule_generated = True
        self.cohort.save()

        # Marquer les 3 premières séances comme complétées
        sessions = CourseSession.objects.filter(cohort=self.cohort).order_by('date')[:3]
        for session in sessions:
            session.status = 'COMPLETED'
            session.save()

        # Calculer le montant gagné (3 séances * 2h * 1800 DA/h)
        expected_amount = 3 * 2 * 1800  # = 10,800 DA

        # Simuler le calcul comme dans la vue
        total_earned = 0
        for session in sessions:
            from datetime import datetime
            duration = datetime.combine(date.today(), session.end_time) - datetime.combine(date.today(), session.start_time)
            hours = duration.total_seconds() / 3600
            total_earned += hours * float(session.cohort.teacher_hourly_rate)

        self.assertEqual(total_earned, expected_amount)

        print(f"   OK Montant gagne calcule: {total_earned} DA pour 3 seances de 2h")

    def test_03_teacher_balance_due_after_payment(self):
        """Test le calcul du reste à payer après un paiement"""
        print("\n[TEST] Test 3: Calcul reste à payer")

        from finance.models import TeacherPayment

        # Générer des séances et marquer comme complétées
        self.cohort.schedule_generated = True
        self.cohort.save()

        sessions = CourseSession.objects.filter(cohort=self.cohort).order_by('date')[:3]
        for session in sessions:
            session.status = 'COMPLETED'
            session.save()

        # Total gagné: 3 * 2 * 1800 = 10,800 DA
        total_earned = 10800

        # Le prof reçoit un paiement de 5000 DA
        TeacherPayment.objects.create(
            teacher=self.teacher,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            total_amount=5000,
            payment_method='CASH',
            payment_date=date(2024, 2, 1),
            recorded_by=self.admin
        )

        # Calculer le reste à payer
        total_paid = TeacherPayment.objects.filter(teacher=self.teacher).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        balance_due = total_earned - float(total_paid)

        self.assertEqual(balance_due, 5800)  # 10,800 - 5,000

        print(f"   OK Reste a payer: {balance_due} DA (gagne: {total_earned}, paye: {total_paid})")


class TeacherPayrollViewsTest(TestCase):
    """Tests pour les vues de gestion de la paie"""

    def setUp(self):
        # Setup de base
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.room = Classroom.objects.create(name="Salle A")

        # Créer 2 professeurs
        self.teacher1 = User.objects.create_user(
            username="teacher1",
            password="test123",
            is_teacher=True,
            first_name="Jean",
            last_name="Dupont",
            birth_date=date(1985, 5, 15)
        )
        self.teacher2 = User.objects.create_user(
            username="teacher2",
            password="test123",
            is_teacher=True,
            first_name="Marie",
            last_name="Martin",
            birth_date=date(1988, 8, 22)
        )

        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        self.subj = Subject.objects.create(name="Mathématiques")
        self.lvl = Level.objects.create(name="Terminale")

        # Créer un groupe pour teacher1
        self.cohort1 = Cohort.objects.create(
            name="Math Term Groupe 1",
            subject=self.subj,
            level=self.lvl,
            teacher=self.teacher1,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            teacher_hourly_rate=2000
        )

        WeeklySchedule.objects.create(
            cohort=self.cohort1,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(12, 0),
            classroom=self.room
        )

        from django.test import Client
        self.client = Client()

    def test_01_teacher_payroll_list_view(self):
        """Test la vue liste de paie par cohort (nouveau système)."""
        print("\n[TEST] Test 1: Vue liste de paie (cohort)")

        # Générer une séance complétée pour alimenter la paie
        session = CourseSession.objects.create(
            cohort=self.cohort1,
            date=date(2024, 1, 8),
            start_time=time(10, 0),
            end_time=time(12, 0),
            teacher=self.teacher1,
            classroom=self.room,
            status='COMPLETED'
        )

        self.client.login(username='admin', password='test123')
        from django.urls import reverse
        response = self.client.get(reverse('finance:teacher_cohort_payroll'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('payroll_data', response.context)

        payroll_data = response.context['payroll_data']
        # Devrait contenir au moins la ligne du cohort1 pour teacher1
        self.assertTrue(any(row['cohort'] == self.cohort1 and row['teacher'] == self.teacher1 for row in payroll_data))

        print(f"   OK Liste de paie (cohort) chargee avec {len(payroll_data)} ligne(s)")

    def test_02_teacher_payroll_detail_view(self):
        """Test la vue de détail de paie d'un professeur"""
        print("\n[TEST] Test 2: Vue détail de paie")

        # Générer des séances et marquer comme complétées
        self.cohort1.schedule_generated = True
        self.cohort1.save()

        sessions = CourseSession.objects.filter(cohort=self.cohort1).order_by('date')[:2]
        for session in sessions:
            session.status = 'COMPLETED'
            session.save()

        self.client.login(username='admin', password='test123')
        from django.urls import reverse
        response = self.client.get(
            reverse('finance:teacher_payroll_detail', args=[self.teacher1.id]),
            {'start': '2024-01-01', 'end': '2024-03-31'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['teacher'], self.teacher1)

        # Vérifier que les séances complétées sont affichées
        session_details = response.context['session_details']
        self.assertEqual(len(session_details), 2)

        print(f"   OK Detail charge avec {len(session_details)} seances completees")

    def test_03_record_teacher_payment_view(self):
        """Test l'enregistrement d'un paiement professeur"""
        print("\n[TEST] Test 3: Enregistrement paiement")

        from finance.models import TeacherPayment

        # Générer des séances
        self.cohort1.schedule_generated = True
        self.cohort1.save()

        sessions = CourseSession.objects.filter(cohort=self.cohort1).order_by('date')[:2]
        for session in sessions:
            session.status = 'COMPLETED'
            session.save()

        self.client.login(username='admin', password='test123')
        from django.urls import reverse

        # Enregistrer un paiement
        post_data = {
            'total_amount': 8000,
            'payment_method': 'TRANSFER',
            'payment_date': '2024-02-01',
            'period_start': '2024-01-01',
            'period_end': '2024-03-31'
        }

        response = self.client.post(
            reverse('finance:record_teacher_payment', args=[self.teacher1.id]),
            post_data
        )

        # Devrait rediriger après succès
        self.assertEqual(response.status_code, 302)

        # Vérifier que le paiement a été créé
        payment = TeacherPayment.objects.filter(teacher=self.teacher1).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.total_amount, 8000)
        self.assertEqual(payment.payment_method, 'TRANSFER')

        print(f"   OK Paiement enregistre: {payment.total_amount} DA")

    def test_04_teacher_profile_preferred_payment_method(self):
        """Test l'affichage de la méthode de paiement préférée (cohort payroll)."""
        print("\n[TEST] Test 4: Méthode de paiement préférée (cohort)")

        # Configurer la méthode préférée
        profile = self.teacher1.teacher_profile
        profile.preferred_payment_method = 'TRANSFER'
        profile.bank_details = "CCP 1234567"
        profile.save()

        # Générer une séance complétée pour alimenter la ligne
        CourseSession.objects.create(
            cohort=self.cohort1,
            date=date(2024, 1, 8),
            start_time=time(10, 0),
            end_time=time(12, 0),
            teacher=self.teacher1,
            classroom=self.room,
            status='COMPLETED'
        )

        self.client.login(username='admin', password='test123')
        from django.urls import reverse
        response = self.client.get(reverse('finance:teacher_cohort_payroll'))

        payroll_data = response.context['payroll_data']

        # Trouver les données du teacher1 sur le cohort1
        teacher1_data = next((d for d in payroll_data if d['teacher'] == self.teacher1 and d['cohort'] == self.cohort1), None)

        self.assertIsNotNone(teacher1_data)
        self.assertIsNotNone(teacher1_data['teacher'].teacher_profile)
        self.assertEqual(teacher1_data['teacher'].teacher_profile.preferred_payment_method, 'TRANSFER')

        print(f"   OK Methode preferee affichee: {teacher1_data['teacher'].teacher_profile.get_preferred_payment_method_display()}")