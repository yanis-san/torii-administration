from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.models import AcademicYear, Classroom
from academics.models import Subject, Level, Cohort, CourseSession
from students.models import Student, Enrollment, Attendance, StudentAnnualFee
from finance.models import Tariff, Payment, TeacherPayment, TeacherCohortPayment

from datetime import date, timedelta, datetime, time
import random


class Command(BaseCommand):
    help = "Seed the database with a comprehensive demo dataset (payments, cohorts, payroll, packs)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-reset",
            action="store_true",
            help="Do not purge existing data before seeding",
        )
        parser.add_argument(
            "--admin-password",
            default="Admin12345!",
            help="Password for the created superuser (default: Admin12345!)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        do_reset = not options.get("no_reset", False)
        admin_password = options.get("admin_password", "Admin12345!")

        if do_reset:
            self.stdout.write(self.style.WARNING("Resetting existing data..."))
            # Delete in safe order (respect PROTECT FKs)
            # Finance first so cohorts can be removed
            TeacherCohortPayment.objects.all().delete()
            TeacherPayment.objects.all().delete()
            Payment.objects.all().delete()

            Attendance.objects.all().delete()
            CourseSession.objects.all().delete()
            Enrollment.objects.all().delete()
            Student.objects.all().delete()
            Cohort.objects.all().delete()
            Subject.objects.all().delete()
            Level.objects.all().delete()
            Classroom.objects.all().delete()
            Tariff.objects.all().delete()
            AcademicYear.objects.all().delete()
            # Users last (will recreate admin/teachers)
            User.objects.all().delete()

        # 1) Academic Years
        today = date.today()
        y1 = AcademicYear.objects.create(
            label="2024-2025",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            is_current=True,
        )
        y2 = AcademicYear.objects.create(
            label="2025-2026",
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 30),
            is_current=False,
        )

        # 2) Users: 1 admin + 4 teachers
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password=admin_password,
            first_name="Administrateur",
            last_name="Système",
        )

        teachers = [
            {
                "username": "prof_jp",
                "first_name": "Marie",
                "last_name": "Sato",
            },
            {
                "username": "prof_cn",
                "first_name": "Li",
                "last_name": "Wei",
            },
            {
                "username": "prof_kr",
                "first_name": "Min",
                "last_name": "Kim",
            },
            {
                "username": "prof_multi",
                "first_name": "Alex",
                "last_name": "Dupont",
            },
        ]

        teacher_users = []
        for t in teachers:
            u = User.objects.create_user(
                username=t["username"],
                password="Teacher123!",
                first_name=t["first_name"],
                last_name=t["last_name"],
                is_teacher=True,
                is_staff=True,
            )
            teacher_users.append(u)

        t_jp, t_cn, t_kr, t_multi = teacher_users

        # 3) Classrooms
        room_tokyo = Classroom.objects.create(name="Salle Tokyo", capacity=18)
        room_seoul = Classroom.objects.create(name="Salle Seoul", capacity=16)
        room_beijing = Classroom.objects.create(name="Salle Beijing", capacity=20)
        room_virtual = Classroom.objects.create(name="Classe Virtuelle", capacity=100)

        # 4) Subjects & Levels
        subj_jp = Subject.objects.create(name="Japonais")
        subj_cn = Subject.objects.create(name="Chinois")
        subj_kr = Subject.objects.create(name="Coréen")

        lvl_debut = Level.objects.create(name="Débutant")
        lvl_inter = Level.objects.create(name="Intermédiaire")
        lvl_avance = Level.objects.create(name="Avancé")

        # 5) Tariffs
        tariff_jp_pres = Tariff.objects.create(name="2025 - Japonais Groupe (Présentiel)", amount=30000)
        tariff_jp_online = Tariff.objects.create(name="2025 - Japonais Groupe (En ligne)", amount=25000)
        tariff_cn_pres = Tariff.objects.create(name="2025 - Chinois Groupe (Présentiel)", amount=28000)
        tariff_kr_online = Tariff.objects.create(name="2025 - Coréen Groupe (En ligne)", amount=22000)
        tariff_pack_10 = Tariff.objects.create(name="Pack Individuel 10h", amount=40000)
        tariff_pack_20 = Tariff.objects.create(name="Pack Individuel 20h", amount=75000)
        tariff_monthly = Tariff.objects.create(name="Forfait Groupe Mensuel (Total 36k)", amount=36000)

        # 6) Cohorts (y1 mostly), covering modalities and types
        c_jp_pres = Cohort.objects.create(
            name="JP N2 Présentiel",
            subject=subj_jp,
            level=lvl_inter,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_jp,
            substitute_teacher=t_multi,
            teacher_hourly_rate=2000,
            standard_price=tariff_jp_pres.amount,
            modality="IN_PERSON",
            is_individual=False,
        )

        c_jp_online = Cohort.objects.create(
            name="JP N3 Online",
            subject=subj_jp,
            level=lvl_debut,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_jp,
            substitute_teacher=t_multi,
            teacher_hourly_rate=1800,
            standard_price=tariff_jp_online.amount,
            modality="ONLINE",
            is_individual=False,
        )

        c_cn_pres = Cohort.objects.create(
            name="CN Débutant Présentiel",
            subject=subj_cn,
            level=lvl_debut,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_cn,
            substitute_teacher=None,
            teacher_hourly_rate=1700,
            standard_price=tariff_cn_pres.amount,
            modality="IN_PERSON",
            is_individual=False,
        )

        c_kr_online = Cohort.objects.create(
            name="KR Online Avancé",
            subject=subj_kr,
            level=lvl_avance,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_kr,
            substitute_teacher=None,
            teacher_hourly_rate=1900,
            standard_price=tariff_kr_online.amount,
            modality="ONLINE",
            is_individual=False,
        )

        # Individual (PACK) cohorts (one online, one in-person)
        c_jp_pack_online = Cohort.objects.create(
            name="JP Coaching 1:1 (Online)",
            subject=subj_jp,
            level=lvl_inter,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_multi,
            substitute_teacher=None,
            teacher_hourly_rate=2500,
            standard_price=tariff_pack_10.amount,
            modality="ONLINE",
            is_individual=True,
        )

        c_cn_pack_pres = Cohort.objects.create(
            name="CN Coaching 1:1 (Présentiel)",
            subject=subj_cn,
            level=lvl_debut,
            academic_year=y1,
            start_date=y1.start_date,
            end_date=y1.end_date,
            teacher=t_cn,
            substitute_teacher=None,
            teacher_hourly_rate=2600,
            standard_price=tariff_pack_20.amount,
            modality="IN_PERSON",
            is_individual=True,
        )

        # 7) Students
        def mk_student(idx, first, last, sex):
            return Student.objects.create(
                first_name=first,
                last_name=last,
                sex=sex,
                email=f"{first.lower()}.{last.lower()}@example.com",
                phone=f"0550{idx:04d}",
                phone_2=f"0770{idx:04d}",
                student_code=f"STU{idx:03d}",
            )

        students = [
            mk_student(1, "Yuki", "Tanaka", "F"),
            mk_student(2, "Kenji", "Ito", "H"),
            mk_student(3, "Aiko", "Kato", "F"),
            mk_student(4, "Wei", "Zhang", "H"),
            mk_student(5, "Mei", "Chen", "F"),
            mk_student(6, "Hana", "Park", "F"),
            mk_student(7, "Jin", "Lee", "H"),
            mk_student(8, "Sora", "Kim", "F"),
            mk_student(9, "Min", "Choi", "H"),
            mk_student(10, "Sara", "Yamamoto", "F"),
            mk_student(11, "Taro", "Suzuki", "H"),
            mk_student(12, "Rin", "Sato", "F"),
        ]

        # 8) Enrollments + Payments across plans
        rng = random.Random(42)

        def pay(enrollment, amounts):
            for amt in amounts:
                Payment.objects.create(
                    enrollment=enrollment,
                    amount=amt,
                    method="CASH",
                    recorded_by=admin,
                )

        # JP Présentiel (3 students FULL/partial/unpaid)
        e1 = Enrollment.objects.create(student=students[0], cohort=c_jp_pres, tariff=tariff_jp_pres, payment_plan='FULL')
        pay(e1, [30000])  # fully paid

        e2 = Enrollment.objects.create(student=students[1], cohort=c_jp_pres, tariff=tariff_jp_pres, payment_plan='FULL')
        pay(e2, [15000])  # partial

        e3 = Enrollment.objects.create(student=students[2], cohort=c_jp_pres, tariff=tariff_jp_pres, payment_plan='FULL')
        # unpaid

        # JP Online (mix FULL and MONTHLY)
        e4 = Enrollment.objects.create(student=students[9], cohort=c_jp_online, tariff=tariff_jp_online, payment_plan='MONTHLY')
        pay(e4, [8000, 7000])  # partial monthly

        e5 = Enrollment.objects.create(student=students[10], cohort=c_jp_online, tariff=tariff_jp_online, payment_plan='FULL')
        pay(e5, [25000])  # paid

        e6 = Enrollment.objects.create(student=students[11], cohort=c_jp_online, tariff=tariff_monthly, payment_plan='MONTHLY')
        pay(e6, [12000])  # partial on different tariff

        # CN Présentiel (mix FULL/unpaid)
        e7 = Enrollment.objects.create(student=students[3], cohort=c_cn_pres, tariff=tariff_cn_pres, payment_plan='FULL')
        pay(e7, [10000])

        e8 = Enrollment.objects.create(student=students[4], cohort=c_cn_pres, tariff=tariff_cn_pres, payment_plan='FULL')
        # unpaid

        # KR Online (one paid, one partial)
        e9 = Enrollment.objects.create(student=students[5], cohort=c_kr_online, tariff=tariff_kr_online, payment_plan='FULL')
        pay(e9, [22000])

        e10 = Enrollment.objects.create(student=students[6], cohort=c_kr_online, tariff=tariff_kr_online, payment_plan='FULL')
        pay(e10, [5000])

        # Individual PACKs
        e_pack_jp = Enrollment.objects.create(
            student=students[7], cohort=c_jp_pack_online, tariff=tariff_pack_10, payment_plan='PACK',
            hours_purchased=10, hours_consumed=0
        )
        pay(e_pack_jp, [20000])  # partial

        e_pack_cn = Enrollment.objects.create(
            student=students[8], cohort=c_cn_pack_pres, tariff=tariff_pack_20, payment_plan='PACK',
            hours_purchased=20, hours_consumed=0
        )
        pay(e_pack_cn, [50000])  # partial

        # 9) Sessions (past completed + upcoming), some with overrides and substitutes
        def daterange(days_back_start=28, count=6, step=4):
            base = today - timedelta(days=days_back_start)
            return [base + timedelta(days=step * i) for i in range(count)]

        def make_sessions_for_cohort(cohort, room, teacher, completed_count=5, scheduled_count=2, with_sub=False):
            sessions = []
            dates = daterange()
            # Completed
            for i in range(completed_count):
                d = dates[i]
                sess_teacher = teacher
                if with_sub and i % 3 == 2:
                    sess_teacher = t_multi
                s = CourseSession.objects.create(
                    cohort=cohort,
                    date=d,
                    start_time=time(9, 0),
                    end_time=time(10, 30),
                    teacher=sess_teacher,
                    classroom=room,
                    status='COMPLETED',
                )
                # Add an override on one session
                if i == 1:
                    s.duration_override_minutes = 90  # 1.5h same as default, just to test override path
                    s.save()
                sessions.append(s)
            # Scheduled upcoming
            for j in range(scheduled_count):
                d = today + timedelta(days=3 * (j + 1))
                s = CourseSession.objects.create(
                    cohort=cohort,
                    date=d,
                    start_time=time(9, 0),
                    end_time=time(10, 30),
                    teacher=teacher,
                    classroom=room,
                    status='SCHEDULED',
                )
                sessions.append(s)
            return sessions

        sessions_jp_pres = make_sessions_for_cohort(c_jp_pres, room_tokyo, t_jp, with_sub=True)
        sessions_jp_online = make_sessions_for_cohort(c_jp_online, room_virtual, t_jp, with_sub=True)
        sessions_cn_pres = make_sessions_for_cohort(c_cn_pres, room_beijing, t_cn)
        sessions_kr_online = make_sessions_for_cohort(c_kr_online, room_virtual, t_kr)
        sessions_pack_jp = make_sessions_for_cohort(c_jp_pack_online, room_virtual, t_multi)
        sessions_pack_cn = make_sessions_for_cohort(c_cn_pack_pres, room_seoul, t_cn)

        # 10) Attendance is auto-created by signals on CourseSession creation.
        # Adjust some attendance lines for PACK cohorts to simulate free/offered sessions
        # and trigger consumed-hours recalculation via post_save.

        # JP PACK: mark one completed session as non-billable to show a free session
        completed_pack_jp = [s for s in sessions_pack_jp if s.status == 'COMPLETED']
        for idx, s in enumerate(completed_pack_jp):
            try:
                att = Attendance.objects.get(session=s, enrollment=e_pack_jp)
                if idx == 2:
                    att.billable = False
                else:
                    att.billable = True
                att.save()  # triggers recalc for PACK
            except Attendance.DoesNotExist:
                pass

        # CN PACK: keep all completed sessions billable; force a save on first to trigger recalc
        completed_pack_cn = [s for s in sessions_pack_cn if s.status == 'COMPLETED']
        if completed_pack_cn:
            try:
                att = Attendance.objects.get(session=completed_pack_cn[0], enrollment=e_pack_cn)
                att.note = (att.note or "") + " seed"
                att.save()
            except Attendance.DoesNotExist:
                pass

        # 12) Mark some annual fees as paid to showcase both states
        if y1:
            for s in (students[0], students[3]):
                fee, _ = StudentAnnualFee.objects.get_or_create(student=s, academic_year=y1, defaults={'amount': 1000})
                fee.is_paid = True
                fee.paid_at = timezone.now()
                fee.save()

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("Users:"))
        self.stdout.write(" - admin / {}".format(admin_password))
        for u in teacher_users:
            self.stdout.write(f" - {u.username} / Teacher123!")
