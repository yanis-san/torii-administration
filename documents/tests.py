from datetime import date

from django.test import TestCase
from django.urls import reverse

from academics.models import Cohort, Level, Subject
from core.models import AcademicYear, User


class DocumentsAccessTestCase(TestCase):
	def setUp(self):
		self.year = AcademicYear.objects.create(
			label="2025-2026",
			start_date=date(2025, 9, 1),
			end_date=date(2026, 8, 31),
			is_current=True,
		)
		self.subject = Subject.objects.create(name="Japonais")
		self.level = Level.objects.create(name="N5")

		self.superuser = User.objects.create_user(
			username="root",
			password="test123",
			is_superuser=True,
			is_staff=True,
			birth_date=date(1980, 1, 1),
		)
		self.teacher_a = User.objects.create_user(
			username="teacher_a",
			password="test123",
			is_teacher=True,
			birth_date=date(1990, 1, 1),
		)
		self.teacher_b = User.objects.create_user(
			username="teacher_b",
			password="test123",
			is_teacher=True,
			birth_date=date(1991, 1, 1),
		)

		self.cohort_a = Cohort.objects.create(
			name="Cohort A",
			subject=self.subject,
			level=self.level,
			teacher=self.teacher_a,
			start_date=date(2025, 9, 15),
			end_date=date(2026, 1, 15),
			academic_year=self.year,
			teacher_hourly_rate=1000,
		)
		self.cohort_b = Cohort.objects.create(
			name="Cohort B",
			subject=self.subject,
			level=self.level,
			teacher=self.teacher_b,
			start_date=date(2025, 9, 15),
			end_date=date(2026, 1, 15),
			academic_year=self.year,
			teacher_hourly_rate=1000,
		)

	def test_teacher_sees_only_linked_cohorts_on_documents_page(self):
		self.client.login(username="teacher_a", password="test123")
		response = self.client.get(reverse("documents:select_cohort"))

		self.assertEqual(response.status_code, 200)
		cohorts = response.context["cohorts"]
		self.assertIn(self.cohort_a, cohorts)
		self.assertNotIn(self.cohort_b, cohorts)
		self.assertNotContains(response, "SYNCHRONISATION")

	def test_superuser_sees_all_cohorts_on_documents_page(self):
		self.client.login(username="root", password="test123")
		response = self.client.get(reverse("documents:select_cohort"))

		self.assertEqual(response.status_code, 200)
		cohorts = response.context["cohorts"]
		self.assertIn(self.cohort_a, cohorts)
		self.assertIn(self.cohort_b, cohorts)

	def test_teacher_cannot_access_global_documents_exports(self):
		self.client.login(username="teacher_a", password="test123")

		response_global = self.client.get(reverse("documents:global_reports"))
		response_zip = self.client.get(reverse("documents:download_all_cohorts_zip"))

		self.assertEqual(response_global.status_code, 404)
		self.assertEqual(response_zip.status_code, 404)
