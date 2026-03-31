# students/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, time
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import User, AcademicYear, Classroom
from academics.models import Subject, Level, Cohort
from students.models import Student, Enrollment
from finance.models import Tariff, Payment


class StudentModelTest(TestCase):
    """Tests pour le modèle Student"""

    def setUp(self):
        self.student = Student.objects.create(
            first_name="Alice", last_name="Durand", phone="0555123456", phone_2="", email="alice@example.com", student_code="ST-TEST-001", birth_date=date(2005, 3, 15)
        )

    def test_01_student_creation(self):
        """Test la création d'un étudiant"""
        print("\n[TEST] Test 1: Création d'un étudiant")

        self.assertEqual(self.student.first_name, "Alice")
        self.assertEqual(self.student.last_name, "Durand")
        self.assertEqual(self.student.phone, "0555123456")
        self.assertTrue(self.student.student_code)  # Code auto-généré

        print(f"   OK Etudiant cree: {self.student.first_name} {self.student.last_name}")
        print(f"   OK Code etudiant: {self.student.student_code}")

    def test_02_student_code_uniqueness(self):
        """Test l'unicité du code étudiant"""
        print("\n[TEST] Test 2: Unicité du code étudiant")

        student2 = Student.objects.create(
            first_name="Bob", last_name="Martin", phone="0555654321", phone_2="", student_code="ST-TEST-002", birth_date=date(2006, 7, 22)
        )

        # Les codes doivent être différents
        self.assertNotEqual(self.student.student_code, student2.student_code)

        print(f"   OK Codes uniques: {self.student.student_code} != {student2.student_code}")

    def test_03_student_full_name(self):
        """Test la méthode __str__"""
        print("\n[TEST] Test 3: Représentation string de l'étudiant")

        expected = "DURAND Alice"
        self.assertEqual(str(self.student), expected)

        print(f"   OK Representation: {str(self.student)}")


class StudentProfilePictureTest(TestCase):
    """Tests pour les photos de profil des étudiants"""

    def setUp(self):
        self.student = Student.objects.create(
            first_name="Test", last_name="Student", phone="0555000000", phone_2="", student_code="ST-TEST-003", birth_date=date(2005, 1, 1)
        )

    def create_test_image(self):
        """Crée une image de test en mémoire"""
        file = BytesIO()
        image = Image.new('RGB', (100, 100), color='blue')
        image.save(file, 'png')
        file.name = 'test_student.png'
        file.seek(0)
        return SimpleUploadedFile(
            name='test_student.png',
            content=file.read(),
            content_type='image/png'
        )

    def test_01_student_profile_picture_upload(self):
        """Test l'upload d'une photo de profil étudiant"""
        print("\n[TEST] Test 1: Upload photo de profil étudiant")

        # Initialement, pas de photo
        self.assertFalse(self.student.profile_picture)

        # Upload d'une photo
        test_image = self.create_test_image()
        self.student.profile_picture = test_image
        self.student.save()

        # Vérifier que la photo est bien enregistrée
        self.student.refresh_from_db()
        self.assertTrue(self.student.profile_picture)
        self.assertIn('profiles/students/', self.student.profile_picture.name)

        print(f"   OK Photo uploadee: {self.student.profile_picture.name}")


class EnrollmentTest(TestCase):
    """Tests pour le modèle Enrollment"""

    def setUp(self):
        # Setup de base
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.subject = Subject.objects.create(name="Français")
        self.level = Level.objects.create(name="Seconde")
        self.cohort = Cohort.objects.create(
            name="Français Seconde",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=1800
        )
        self.student = Student.objects.create(
            first_name="Alice", last_name="Durand", phone="0555111111", phone_2="", student_code="ST-TEST-004", birth_date=date(2005, 3, 15)
        )
        self.tariff = Tariff.objects.create(name="Standard", amount=8000)

    def test_01_enrollment_creation(self):
        """Test la création d'une inscription"""
        print("\n[TEST] Test 1: Création d'une inscription")

        enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL'
        )

        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.cohort, self.cohort)
        self.assertEqual(enrollment.balance_due, 8000)  # Montant initial du tarif

        print(f"   OK Inscription creee pour {self.student} dans {self.cohort}")
        print(f"   OK Montant du: {enrollment.balance_due} DA")

    def test_02_enrollment_balance_after_payment(self):
        """Test le calcul du solde après paiement"""
        print("\n[TEST] Test 2: Calcul du solde après paiement")

        enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL'
        )

        # Paiement de 3000 DA
        Payment.objects.create(
            enrollment=enrollment,
            amount=3000,
            method='CASH',
            recorded_by=self.teacher
        )

        # Le solde devrait être 8000 - 3000 = 5000
        self.assertEqual(enrollment.balance_due, 5000)

        print(f"   OK Apres paiement de 3000 DA, reste: {enrollment.balance_due} DA")


class StudentListViewTest(TestCase):
    """Tests pour la vue de liste des étudiants"""

    def setUp(self):
        # Créer des étudiants
        self.student1 = Student.objects.create(
            first_name="Alice", last_name="Durand", phone="0555111111", phone_2="", student_code="ST-TEST-004",
            email="alice@test.com", birth_date=date(2005, 3, 15)
        )
        self.student2 = Student.objects.create(
            first_name="Bob", last_name="Martin", phone="0555222222", phone_2="", email="bob@test.com", student_code="ST-TEST-005", birth_date=date(2006, 7, 22)
        )

        # Créer un utilisateur admin pour se connecter
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        self.client = Client()
        self.client.login(username='admin', password='test123')

    def test_01_student_list_view_loads(self):
        """Test que la page de liste se charge correctement"""
        print("\n[TEST] Test 1: Chargement de la liste des étudiants")

        response = self.client.get(reverse('students:list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('students', response.context)

        # Vérifier que les 2 étudiants sont présents
        students = response.context['students']
        self.assertEqual(students.paginator.count, 2)

        print(f"   OK Page chargee avec {students.paginator.count} etudiants")

    def test_02_student_search(self):
        """Test la recherche d'étudiants"""
        print("\n[TEST] Test 2: Recherche d'étudiants")

        # Recherche par prénom
        response = self.client.get(reverse('students:list'), {'q': 'Alice'})

        students = response.context['students']
        self.assertEqual(students.paginator.count, 1)
        self.assertEqual(students.object_list[0].first_name, "Alice")

        print(f"   OK Recherche 'Alice' trouvee: {students.object_list[0]}")

    def test_03_student_filter_by_cohort(self):
        """Test le filtrage par groupe"""
        print("\n[TEST] Test 3: Filtrage par groupe")

        # Setup: créer un groupe et inscrire un étudiant
        ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        teacher = User.objects.create_user(username="teacher", is_teacher=True, birth_date=date(1985, 5, 15))
        subject = Subject.objects.create(name="Math")
        level = Level.objects.create(name="Terminale")
        cohort = Cohort.objects.create(
            name="Math Term",
            subject=subject,
            level=level,
            teacher=teacher,
            academic_year=ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=2000
        )
        tariff = Tariff.objects.create(name="Standard", amount=5000)

        Enrollment.objects.create(
            student=self.student1,
            cohort=cohort,
            tariff=tariff,
            payment_plan='FULL'
        )

        # Filtrer par ce groupe
        response = self.client.get(reverse('students:list'), {'cohort': cohort.id})

        students = response.context['students']
        self.assertEqual(students.paginator.count, 1)
        self.assertEqual(students.object_list[0], self.student1)

        print(f"   OK Filtrage par '{cohort.name}' trouve: {students.object_list[0]}")


class StudentDetailViewTest(TestCase):
    """Tests pour la vue de détail d'un étudiant"""

    def setUp(self):
        self.student = Student.objects.create(
            first_name="Alice",
            last_name="Durand",
            phone="0555123456",
            phone_2="",
            email="alice@test.com",
            birth_date=date(2005, 3, 15)
        )

        # Créer un groupe et une inscription
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.teacher = User.objects.create_user(username="teacher", is_teacher=True, birth_date=date(1985, 5, 15))
        self.subject = Subject.objects.create(name="Anglais")
        self.level = Level.objects.create(name="B1")
        self.cohort = Cohort.objects.create(
            name="Anglais B1",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=1500
        )
        self.tariff = Tariff.objects.create(name="Standard", amount=7000)

        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL'
        )

        # Créer un admin pour se connecter
        self.admin = User.objects.create_user(
            username="admin",
            password="test123",
            is_staff=True,
            is_superuser=True,
            birth_date=date(1980, 1, 10)
        )

        self.client = Client()
        self.client.login(username='admin', password='test123')

    def test_01_student_detail_view_loads(self):
        """Test que la page de détail se charge"""
        print("\n[TEST] Test 1: Chargement de la page de détail")

        response = self.client.get(reverse('students:detail', args=[self.student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['student'], self.student)

        print(f"   OK Page de detail chargee pour {self.student}")

    def test_02_enrollments_displayed(self):
        """Test que les inscriptions sont affichées"""
        print("\n[TEST] Test 2: Affichage des inscriptions")

        response = self.client.get(reverse('students:detail', args=[self.student.id]))

        enrollments = response.context['enrollments']
        self.assertEqual(enrollments.count(), 1)
        self.assertEqual(enrollments.first().cohort, self.cohort)

        print(f"   OK 1 inscription affichee: {enrollments.first().cohort.name}")

    def test_03_balance_displayed(self):
        """Test que le solde est affiché correctement"""
        print("\n[TEST] Test 3: Affichage du solde")

        response = self.client.get(reverse('students:detail', args=[self.student.id]))

        enrollments = response.context['enrollments']
        enrollment = enrollments.first()

        # Le solde initial devrait être égal au tarif
        self.assertEqual(enrollment.balance_due, 7000)

        print(f"   OK Solde affiche: {enrollment.balance_due} DA")

    def test_04_payments_history_displayed(self):
        """Test que l'historique des paiements est affiché"""
        print("\n[TEST] Test 4: Affichage de l'historique des paiements")

        # Ajouter quelques paiements
        Payment.objects.create(
            enrollment=self.enrollment,
            amount=2000,
            method='CASH',
            recorded_by=self.teacher
        )
        Payment.objects.create(
            enrollment=self.enrollment,
            amount=3000,
            method='TRANSFER',
            recorded_by=self.teacher
        )

        response = self.client.get(reverse('students:detail', args=[self.student.id]))

        enrollments = response.context['enrollments']
        enrollment = enrollments.first()
        payments = enrollment.payments.all()

        self.assertEqual(payments.count(), 2)
        self.assertEqual(enrollment.balance_due, 2000)  # 7000 - 2000 - 3000

        print(f"   OK {payments.count()} paiements affiches")
        print(f"   OK Solde restant: {enrollment.balance_due} DA")


class AttendanceSignalsTest(TestCase):
    """Tests pour les signaux automatiques de création de présences"""

    def setUp(self):
        # Setup de base
        from academics.models import CourseSession
        from students.models import Attendance

        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.subject = Subject.objects.create(name="Mathématiques")
        self.level = Level.objects.create(name="Terminale")
        self.classroom = Classroom.objects.create(name="Salle A")
        self.cohort = Cohort.objects.create(
            name="Maths Terminale",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=2000
        )
        self.student1 = Student.objects.create(
            first_name="Alice", last_name="Durand", phone="0555111111",
            student_code="ST-TEST-ATT-001", birth_date=date(2005, 3, 15)
        )
        self.student2 = Student.objects.create(
            first_name="Bob", last_name="Martin", phone="0555222222",
            student_code="ST-TEST-ATT-002", birth_date=date(2006, 7, 22)
        )
        self.tariff = Tariff.objects.create(name="Standard", amount=8000)

    def test_01_attendance_created_on_enrollment(self):
        """Test que les présences sont créées automatiquement lors d'une inscription"""
        from academics.models import CourseSession
        from students.models import Attendance
        from django.utils import timezone
        from datetime import timedelta

        print("\n[TEST] Test 1: Création automatique des présences à l'inscription")

        # Créer une séance future (demain)
        tomorrow = timezone.now().date() + timedelta(days=1)
        session = CourseSession.objects.create(
            cohort=self.cohort,
            date=tomorrow,
            start_time=time(9, 0),
            end_time=time(11, 0),
            status='SCHEDULED',
            teacher=self.teacher,
            classroom=self.classroom
        )

        # Inscrire un étudiant
        enrollment = Enrollment.objects.create(
            student=self.student1,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL',
            is_active=True
        )

        # Vérifier que la présence a été créée automatiquement
        attendance = Attendance.objects.filter(
            session=session,
            student=self.student1
        )

        self.assertTrue(attendance.exists())
        self.assertEqual(attendance.first().status, 'PRESENT')
        self.assertTrue(attendance.first().billable)

        print(f"   OK Presence creee automatiquement pour {self.student1} a la seance du {tomorrow}")

    def test_02_attendance_created_on_session_creation(self):
        """Test que les présences sont créées pour tous les étudiants lors de la création d'une séance"""
        from academics.models import CourseSession
        from students.models import Attendance

        print("\n[TEST] Test 2: Création automatique des présences lors de la création d'une séance")

        # Inscrire deux étudiants
        enrollment1 = Enrollment.objects.create(
            student=self.student1,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL',
            is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student2,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='PACK',
            is_active=True
        )

        # Créer une nouvelle séance
        session = CourseSession.objects.create(
            cohort=self.cohort,
            date=date(2024, 4, 10),
            start_time=time(14, 0),
            end_time=time(16, 0),
            status='SCHEDULED',
            teacher=self.teacher,
            classroom=self.classroom
        )

        # Vérifier que les présences ont été créées pour les deux étudiants
        attendances = Attendance.objects.filter(session=session)

        self.assertEqual(attendances.count(), 2)
        self.assertTrue(attendances.filter(student=self.student1).exists())
        self.assertTrue(attendances.filter(student=self.student2).exists())

        print(f"   OK {attendances.count()} presences creees automatiquement pour la seance")


class AttendancePersistenceTest(TestCase):
    """Tests pour la persistance des présences en base de données"""

    def setUp(self):
        from academics.models import CourseSession

        # Setup complet
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="test123",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.subject = Subject.objects.create(name="Physique")
        self.level = Level.objects.create(name="Première")
        self.classroom = Classroom.objects.create(name="Salle B")
        self.cohort = Cohort.objects.create(
            name="Physique Première",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=1800
        )
        self.student = Student.objects.create(
            first_name="Charlie", last_name="Dupont", phone="0555333333",
            student_code="ST-TEST-PERSIST-001", birth_date=date(2005, 8, 20)
        )
        self.tariff = Tariff.objects.create(name="Standard", amount=7000)
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL',
            is_active=True
        )
        self.session = CourseSession.objects.create(
            cohort=self.cohort,
            date=date(2024, 2, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            status='SCHEDULED',
            teacher=self.teacher,
            classroom=self.classroom
        )

        # Créer un client pour les tests de vues
        self.client = Client()
        self.client.login(username='teacher', password='test123')

    def test_01_attendance_persists_after_update(self):
        """Test que les présences sont bien stockées et persistent après modification"""
        from students.models import Attendance

        print("\n[TEST] Test 1: Persistance des présences après modification")

        # Marquer l'étudiant comme absent
        response = self.client.post(
            reverse('academics:session_detail', args=[self.session.id]),
            {
                f'status_{self.student.id}': 'ABSENT',
                'session_note': 'Test de persistance'
            }
        )

        # Rafraîchir les objets depuis la base de données
        self.session.refresh_from_db()

        # Vérifier que la présence a été mise à jour
        attendance = Attendance.objects.get(
            session=self.session,
            student=self.student
        )

        self.assertEqual(attendance.status, 'ABSENT')
        self.assertEqual(self.session.note, 'Test de persistance')
        self.assertEqual(self.session.status, 'COMPLETED')

        print(f"   OK Statut persiste: {attendance.get_status_display()}")
        print(f"   OK Note de seance: {self.session.note}")

    def test_02_attendance_displayed_correctly(self):
        """Test que les présences stockées sont affichées correctement dans le formulaire"""
        from students.models import Attendance

        print("\n[TEST] Test 2: Affichage correct des présences stockées")

        # Modifier la présence manuellement
        Attendance.objects.filter(
            session=self.session,
            student=self.student
        ).update(status='LATE')

        # Recharger la page
        response = self.client.get(
            reverse('academics:session_detail', args=[self.session.id])
        )

        # Vérifier que le contexte contient le bon statut
        attendance_dict = response.context['attendance_dict']
        self.assertEqual(attendance_dict[self.student.id], 'LATE')

        print(f"   OK Statut affiche correctement: {attendance_dict[self.student.id]}")

    def test_03_hours_consumed_calculated(self):
        """Test que les heures consommées sont bien calculées pour les packs"""
        from students.models import Attendance

        print("\n[TEST] Test 3: Calcul des heures consommées")

        # Changer le plan de paiement en PACK
        self.enrollment.payment_plan = 'PACK'
        self.enrollment.hours_purchased = 10
        self.enrollment.save()

        # Marquer comme présent et facturable
        # Utiliser save() au lieu de update() pour déclencher le signal
        attendance = Attendance.objects.get(
            session=self.session,
            student=self.student
        )
        attendance.status = 'PRESENT'
        attendance.billable = True
        attendance.save()

        # Rafraîchir l'enrollment
        self.enrollment.refresh_from_db()

        # La séance dure 2h (10h-12h)
        self.assertEqual(self.enrollment.hours_consumed, 2.0)

        print(f"   OK Heures consommees: {self.enrollment.hours_consumed}h / {self.enrollment.hours_purchased}h")


class AttendanceDocumentGenerationTest(TestCase):
    """Tests pour la génération de documents avec les vraies présences"""

    def setUp(self):
        from academics.models import CourseSession

        # Setup complet
        self.ay = AcademicYear.objects.create(
            label="2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="test123",
            is_teacher=True,
            birth_date=date(1985, 5, 15)
        )
        self.subject = Subject.objects.create(name="Chimie")
        self.level = Level.objects.create(name="Terminale")
        self.classroom = Classroom.objects.create(name="Labo")
        self.cohort = Cohort.objects.create(
            name="Chimie Terminale",
            subject=self.subject,
            level=self.level,
            teacher=self.teacher,
            academic_year=self.ay,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            teacher_hourly_rate=2200
        )
        self.student1 = Student.objects.create(
            first_name="David", last_name="Bernard", phone="0555444444",
            student_code="ST-TEST-DOC-001", birth_date=date(2005, 4, 10)
        )
        self.student2 = Student.objects.create(
            first_name="Emma", last_name="Laurent", phone="0555555555",
            student_code="ST-TEST-DOC-002", birth_date=date(2006, 9, 5)
        )
        self.tariff = Tariff.objects.create(name="Standard", amount=9000)

        # Créer des inscriptions
        self.enrollment1 = Enrollment.objects.create(
            student=self.student1,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL',
            is_active=True
        )
        self.enrollment2 = Enrollment.objects.create(
            student=self.student2,
            cohort=self.cohort,
            tariff=self.tariff,
            payment_plan='FULL',
            is_active=True
        )

        # Créer des séances
        self.session1 = CourseSession.objects.create(
            cohort=self.cohort,
            date=date(2024, 3, 10),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status='COMPLETED',
            teacher=self.teacher,
            classroom=self.classroom
        )
        self.session2 = CourseSession.objects.create(
            cohort=self.cohort,
            date=date(2024, 3, 17),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status='COMPLETED',
            teacher=self.teacher,
            classroom=self.classroom
        )

        self.client = Client()
        self.client.login(username='teacher', password='test123')

    def test_01_download_session_attendance(self):
        """Test le téléchargement de la liste de présence d'une séance"""
        from students.models import Attendance

        print("\n[TEST] Test 1: Téléchargement de la liste de présence d'une séance")

        # Modifier les statuts
        Attendance.objects.filter(
            session=self.session1,
            student=self.student1
        ).update(status='PRESENT')

        Attendance.objects.filter(
            session=self.session1,
            student=self.student2
        ).update(status='ABSENT')

        # Télécharger le document
        response = self.client.get(
            reverse('documents:download_session_attendance', args=[self.session1.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertIn('attachment', response['Content-Disposition'])

        print(f"   OK Document genere avec succes")
        print(f"   OK Type: {response['Content-Type']}")

    def test_02_download_cohort_attendance(self):
        """Test le téléchargement de la liste complète d'un groupe"""
        from students.models import Attendance

        print("\n[TEST] Test 2: Téléchargement de la liste complète du groupe")

        # Modifier quelques statuts
        Attendance.objects.filter(
            session=self.session1,
            student=self.student1
        ).update(status='PRESENT')

        Attendance.objects.filter(
            session=self.session2,
            student=self.student1
        ).update(status='LATE')

        # Télécharger le document
        response = self.client.get(
            reverse('documents:download_cohort_attendance', args=[self.cohort.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

        print(f"   OK Document complet genere avec succes")
