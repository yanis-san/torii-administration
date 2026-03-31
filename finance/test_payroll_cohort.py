from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from academics.models import Cohort, CourseSession, Subject, Level
from finance.models import TeacherCohortPayment
from core.models import AcademicYear, Classroom


def make_year(start_year: int) -> AcademicYear:
    return AcademicYear.objects.create(
        label=f"{start_year}-{start_year+1}",
        start_date=date(start_year, 9, 1),
        end_date=date(start_year + 1, 6, 30),
        is_current=True,
    )


class PayrollCohortTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="teacher1", password="pass", first_name="Tea", last_name="Cher", is_teacher=True
        )
        self.staff = get_user_model().objects.create_user(
            username="staff", password="pass", is_staff=True
        )

        self.year = make_year(2025)
        self.subject = Subject.objects.create(name="Math")
        self.level = Level.objects.create(name="Grade 1")
        self.classroom = Classroom.objects.create(name="A1", capacity=20)

        self.cohort = Cohort.objects.create(
            name="Cohort A",
            subject=self.subject,
            level=self.level,
            academic_year=self.year,
            start_date=date(2025, 10, 1),
            end_date=date(2026, 3, 31),
            teacher=self.user,
            teacher_hourly_rate=2000,
        )

        # Create sessions: 4 completed, 1 cancelled, 1 scheduled
        base_day = date(2025, 10, 10)
        for i in range(4):
            CourseSession.objects.create(
                cohort=self.cohort,
                date=base_day + timedelta(days=i),
                start_time=time(9, 0),
                end_time=time(10, 30),  # 1.5 hours
                status='COMPLETED',
                teacher=self.user,
                classroom=self.classroom,
            )
        CourseSession.objects.create(
            cohort=self.cohort,
            date=base_day + timedelta(days=5),
            start_time=time(9, 0),
            end_time=time(10, 30),
            status='CANCELLED',
            teacher=self.user,
            classroom=self.classroom,
        )
        CourseSession.objects.create(
            cohort=self.cohort,
            date=base_day + timedelta(days=6),
            start_time=time(9, 0),
            end_time=time(10, 30),
            status='SCHEDULED',
            teacher=self.user,
            classroom=self.classroom,
        )

    def test_session_aggregation_completed_only(self):
        # Expect 4 completed sessions at 1.5h each = 6 hours
        sessions = CourseSession.objects.filter(
            cohort=self.cohort, status='COMPLETED'
        )
        total_minutes = sum(
            int((s.end_time.hour*60 + s.end_time.minute) - (s.start_time.hour*60 + s.start_time.minute))
            for s in sessions
        )
        self.assertEqual(total_minutes, 4 * 90)

        # Amount due based on teacher_hourly_rate (per hour)
        total_hours = total_minutes / 60
        expected_due = int(total_hours * self.cohort.teacher_hourly_rate)
        self.assertEqual(expected_due, int(6 * 2000))

    def test_payment_model_balance_properties(self):
        payment = TeacherCohortPayment.objects.create(
            teacher=self.user,
            cohort=self.cohort,
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
            amount_due=12000,
            amount_paid=5000,
            payment_date=date(2025, 11, 1),
            payment_method="cash",
            recorded_by=self.staff,
        )
        self.assertEqual(payment.balance_due, 7000)
        self.assertFalse(payment.is_fully_paid)

        payment.amount_paid = 12000
        payment.save()
        self.assertEqual(payment.balance_due, 0)
        self.assertTrue(payment.is_fully_paid)

    def test_uniqueness_constraint_duplicate_prevented(self):
        base_kwargs = dict(
            teacher=self.user,
            cohort=self.cohort,
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
            amount_due=12000,
            amount_paid=5000,
            payment_date=date(2025, 11, 1),
            payment_method="cash",
            recorded_by=self.staff,
        )
        TeacherCohortPayment.objects.create(**base_kwargs)
        with self.assertRaises(IntegrityError):
            TeacherCohortPayment.objects.create(**base_kwargs)

    def test_payroll_list_view_no_default_dates(self):
        url = reverse("finance:teacher_cohort_payroll")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Ensure context has None dates (no default pre-selection)
        self.assertIn("period_start", resp.context)
        self.assertIsNone(resp.context.get("period_start"))
        self.assertIsNone(resp.context.get("period_end"))

    def test_detail_view_handles_empty_params(self):
        url = reverse("finance:teacher_cohort_payment_detail", args=[self.cohort.id])
        # Provide empty strings for start/end
        resp = self.client.get(url, {"start": "", "end": ""})
        self.assertEqual(resp.status_code, 200)
        # View should fallback to cohort/session bounds
        self.assertIn("period_start", resp.context)
        self.assertIn("period_end", resp.context)
        self.assertIsInstance(resp.context["period_start"], date)
        self.assertIsInstance(resp.context["period_end"], date)

    def test_record_payment_handles_empty_dates(self):
        url = reverse("finance:record_cohort_payment", args=[self.cohort.id])
        # GET with empty start/end should render fine
        resp_get = self.client.get(url, {"start": "", "end": ""})
        self.assertEqual(resp_get.status_code, 200)

        # POST without period_start/period_end/payment_date should default and create payment
        post_data = {
            "amount_due": "12000",
            "amount_paid": "5000",
            "payment_method": "cash",
            # intentionally omit dates
        }
        self.client.force_login(self.staff)
        resp_post = self.client.post(url, post_data, follow=True)
        self.assertEqual(resp_post.status_code, 200)
        self.assertTrue(
            TeacherCohortPayment.objects.filter(cohort=self.cohort, amount_paid=5000).exists()
        )

    def test_legacy_payroll_redirects(self):
        url = reverse("finance:teacher_payroll_list")
        resp = self.client.get(url, follow=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertTrue(resp.headers.get("Location", "").endswith("/finance/payroll-cohort/"))
