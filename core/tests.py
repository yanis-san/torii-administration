# core/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import User, AcademicYear, Classroom, TeacherProfile
from academics.models import Subject, Level, Cohort, WeeklySchedule, CourseSession
from students.models import Student, Enrollment
from finance.models import Tariff


class TeacherProfileTest(TestCase):
    """Tests pour le modèle TeacherProfile"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher1",
            password="test123",
            first_name="Jean",
            last_name="Dupont",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )

    def test_01_teacher_profile_creation(self):
        """Test la création automatique du TeacherProfile"""
        print("\n[TEST] Test 1: Création automatique TeacherProfile")

        # Le profil devrait être créé automatiquement via signal
        self.assertTrue(hasattr(self.teacher, 'teacher_profile'))
        profile = self.teacher.teacher_profile

        self.assertEqual(profile.user, self.teacher)
        self.assertEqual(profile.preferred_payment_method, 'CASH')  # Valeur par défaut
        print("   ✅ TeacherProfile créé automatiquement avec méthode de paiement par défaut")

    def test_02_teacher_profile_update(self):
        """Test la mise à jour des informations de profil"""
        print("\n[TEST] Test 2: Mise à jour TeacherProfile")

        profile = self.teacher.teacher_profile
        profile.preferred_payment_method = 'TRANSFER'
        profile.bank_details = "CCP 123456789"
        profile.tax_id = "TAX123456"
        profile.notes = "Professeur expérimenté"
        profile.save()

        # Vérifier que les changements sont bien enregistrés
        profile.refresh_from_db()
        self.assertEqual(profile.preferred_payment_method, 'TRANSFER')
        self.assertEqual(profile.bank_details, "CCP 123456789")
        self.assertEqual(profile.tax_id, "TAX123456")
        print("   ✅ Informations du profil mises à jour correctement")


class UserProfilePictureTest(TestCase):
    """Tests pour les photos de profil des utilisateurs"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test123",
            first_name="Test",
            last_name="User",
            birth_date=date(1990, 3, 20)
        )

    def create_test_image(self):
        """Crée une image de test en mémoire"""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(file, 'png')
        file.name = 'test.png'
        file.seek(0)
        return SimpleUploadedFile(
            name='test.png',
            content=file.read(),
            content_type='image/png'
        )

    def test_01_user_profile_picture_upload(self):
        """Test l'upload d'une photo de profil"""
        print("\n[TEST] Test 1: Upload photo de profil utilisateur")

        # Initialement, pas de photo
        self.assertFalse(self.user.profile_picture)

        # Upload d'une photo
        test_image = self.create_test_image()
        self.user.profile_picture = test_image
        self.user.save()

        # Vérifier que la photo est bien enregistrée
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture)
        self.assertIn('profiles/users/', self.user.profile_picture.name)
        print(f"   ✅ Photo uploadée: {self.user.profile_picture.name}")


class TeacherDashboardTest(TestCase):
    """Tests pour le tableau de bord spécifique aux professeurs"""

    def setUp(self):
        # Création des données de base
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.room = Classroom.objects.create(name="Salle A")
        self.subject = Subject.objects.create(name="Mathématiques")
        self.level = Level.objects.create(name="Terminale")

        # Création de 2 professeurs
        self.teacher1 = User.objects.create_user(
            username="teacher1",
            password="test123",
            first_name="Jean",
            last_name="Dupont",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.teacher2 = User.objects.create_user(
            username="teacher2",
            password="test123",
            first_name="Marie",
            last_name="Martin",
            is_teacher=True,
            birth_date=date(1988, 8, 22)
        )

        # Création d'un admin
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        # Création de groupes pour chaque professeur
        self.cohort1 = Cohort.objects.create(
            name="Math Term - Groupe 1",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher1,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=2000
        )

        self.cohort2 = Cohort.objects.create(
            name="Math Term - Groupe 2",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher2,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=2000
        )

        # Création de séances pour aujourd'hui
        today = date.today()
        self.session1 = CourseSession.objects.create(
            cohort=self.cohort1,
            date=today,
            start_time=time(10, 0),
            end_time=time(12, 0),
            teacher=self.teacher1,
            classroom=self.room,
            status='SCHEDULED'
        )

        self.session2 = CourseSession.objects.create(
            cohort=self.cohort2,
            date=today,
            start_time=time(14, 0),
            end_time=time(16, 0),
            teacher=self.teacher2,
            classroom=self.room,
            status='SCHEDULED'
        )

        self.client = Client()

    def test_01_teacher_sees_only_their_sessions(self):
        """Test que le professeur voit uniquement SES séances"""
        print("\n[TEST] Test 1: Dashboard professeur - Filtrage des séances")

        # Connexion en tant que teacher1
        self.client.login(username='teacher1', password='test123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)

        # Vérifier que seules les séances de teacher1 sont affichées
        sessions_in_context = response.context['sessions']
        self.assertEqual(sessions_in_context.count(), 1)
        self.assertEqual(sessions_in_context.first().teacher, self.teacher1)

        print(f"   ✅ Teacher1 voit uniquement ses {sessions_in_context.count()} séance(s)")

    def test_02_teacher_sees_only_their_cohorts(self):
        """Test que le professeur voit uniquement SES groupes"""
        print("\n[TEST] Test 2: Dashboard professeur - Filtrage des groupes")

        # Connexion en tant que teacher1
        self.client.login(username='teacher1', password='test123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_teacher'])

        # Vérifier que seuls les groupes de teacher1 sont affichés
        cohorts_in_context = response.context.get('my_cohorts')
        if cohorts_in_context is not None:
            self.assertEqual(cohorts_in_context.count(), 1)
            self.assertEqual(cohorts_in_context.first().teacher, self.teacher1)
            print(f"   ✅ Teacher1 voit uniquement son groupe: {cohorts_in_context.first().name}")

    def test_03_admin_sees_all_sessions(self):
        """Test que l'admin voit TOUTES les séances"""
        print("\n[TEST] Test 3: Dashboard admin - Voit tout")

        # Connexion en tant qu'admin
        self.client.login(username='admin', password='test123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)

        # Admin devrait voir TOUTES les séances du jour (2 séances)
        sessions_in_context = response.context['sessions']
        self.assertEqual(sessions_in_context.count(), 2)

        print(f"   ✅ Admin voit toutes les {sessions_in_context.count()} séances")

    def test_04_teacher_student_count(self):
        """Test le calcul du nombre d'étudiants d'un professeur"""
        print("\n[TEST] Test 4: Comptage des étudiants du professeur")

        # Créer des étudiants et des inscriptions
        student1 = Student.objects.create(
            first_name="Alice",
            last_name="Durand",
            phone="0555111111",
            phone_2="",
            student_code="ST-CORE-001",
            birth_date=date(2005, 3, 15)
        )
        student2 = Student.objects.create(
            first_name="Bob",
            last_name="Martin",
            phone="0555222222",
            phone_2="",
            student_code="ST-CORE-002",
            birth_date=date(2006, 7, 22)
        )

        tariff = Tariff.objects.create(name="Standard", amount=5000)

        # Inscrire les 2 étudiants dans le groupe de teacher1
        Enrollment.objects.create(
            student=student1,
            cohort=self.cohort1,
            tariff=tariff,
            payment_plan='FULL'
        )
        Enrollment.objects.create(
            student=student2,
            cohort=self.cohort1,
            tariff=tariff,
            payment_plan='FULL'
        )

        # Connexion en tant que teacher1
        self.client.login(username='teacher1', password='test123')
        response = self.client.get(reverse('dashboard'))

        # Le professeur devrait voir 2 étudiants
        total_students = response.context.get('total_students', 0)
        self.assertEqual(total_students, 2)

        print(f"   ✅ Teacher1 a {total_students} étudiants dans ses groupes")


class RoleBasedAccessTest(TestCase):
    """Tests pour les permissions basées sur les rôles"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            password="test123",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )
        self.client = Client()

    def test_01_unauthenticated_redirects_to_login(self):
        """Test que les utilisateurs non authentifiés sont redirigés"""
        print("\n[TEST] Test 1: Redirection vers login si non authentifié")

        response = self.client.get(reverse('dashboard'))

        # Devrait rediriger vers la page de login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)

        print("   ✅ Utilisateur non authentifié redirigé vers login")

    def test_02_teacher_can_access_dashboard(self):
        """Test que les professeurs peuvent accéder au dashboard"""
        print("\n[TEST] Test 2: Professeur accède au dashboard")

        self.client.login(username='teacher', password='test123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_teacher'])

        print("   ✅ Professeur peut accéder au dashboard")

    def test_03_admin_can_access_dashboard(self):
        """Test que les admins peuvent accéder au dashboard"""
        print("\n[TEST] Test 3: Admin accède au dashboard")

        self.client.login(username='admin', password='test123')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)

        print("   ✅ Admin peut accéder au dashboard")
