# students/models.py
from django.db import models
from core.models import User
from academics.models import Cohort
from core.models import AcademicYear
from django.utils import timezone
from finance.models import Tariff

class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(
        max_length=1,
        choices=[('H', 'Homme'), ('F', 'Femme')],
        blank=True,
        default='',
        verbose_name="Sexe"
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    phone_2 = models.CharField(max_length=20)
    birth_date = models.DateField(blank=True, null=True)
    motivation = models.TextField(blank=True, verbose_name="Pourquoi ?")
    # Code étudiant unique (généré auto ou manuel)
    student_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profiles/students/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )

    # Pièce d'identité (recto / verso)
    id_card_front = models.ImageField(
        upload_to='profiles/students/id_cards/',
        blank=True,
        null=True,
        verbose_name="Carte d'identité - recto"
    )
    id_card_back = models.ImageField(
        upload_to='profiles/students/id_cards/',
        blank=True,
        null=True,
        verbose_name="Carte d'identité - verso"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from core.image_utils import compress_image
        
        # Determine if images have changed or are new
        try:
            this = Student.objects.get(id=self.id)
            if this.profile_picture != self.profile_picture:
                self.profile_picture = compress_image(self.profile_picture, max_width=800)
            if this.id_card_front != self.id_card_front:
                self.id_card_front = compress_image(self.id_card_front, max_width=1024)
            if this.id_card_back != self.id_card_back:
                self.id_card_back = compress_image(self.id_card_back, max_width=1024)
        except Student.DoesNotExist:
            # New instance
            if self.profile_picture:
                self.profile_picture = compress_image(self.profile_picture, max_width=800)
            if self.id_card_front:
                self.id_card_front = compress_image(self.id_card_front, max_width=1024)
            if self.id_card_back:
                self.id_card_back = compress_image(self.id_card_back, max_width=1024)
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name.upper()} {self.first_name}"

    @property
    def age(self):
        """Calcule l'âge à partir de la date de naissance"""
        if not self.birth_date:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    def has_paid_registration_fee(self, year: AcademicYear | None = None) -> bool:
        """Vrai si les frais d'inscription annuels sont payés pour l'année donnée (ou l'année active)."""
        if year is None:
            year = AcademicYear.get_current()
        if not year:
            return False
        fee = getattr(self, 'annual_fees', None)
        if fee is None:
            return False
        rec = self.annual_fees.filter(academic_year=year).first()
        return bool(rec and rec.is_paid)

class Enrollment(models.Model):
    """
    LE CONTRAT.
    Lie un étudiant à un groupe, fixe le prix et le mode de paiement.
    """
    PAYMENT_PLANS = [
        ('FULL', 'Totalité (Une fois)'),
        ('MONTHLY', 'Mensuel (Échéancier)'),
        ('PACK', 'Pack d\'Heures (Débit à la séance)'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    cohort = models.ForeignKey(Cohort, on_delete=models.PROTECT, related_name='enrollments')
    
    # Financier
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT, verbose_name="Tarif Appliqué")
    payment_plan = models.CharField(max_length=10, choices=PAYMENT_PLANS, default='FULL')
    discount = models.ForeignKey('finance.Discount', on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    
    # Crédits d'heures (Pour le mode PACK/Individuel)
    hours_purchased = models.DecimalField(default=0, max_digits=5, decimal_places=1, help_text="Si Pack d'heures")
    hours_consumed = models.DecimalField(default=0, max_digits=5, decimal_places=1)

    is_active = models.BooleanField(default=True)
    date = models.DateField(auto_now_add=True)
    # Code contrat: ex "20242025-JP-PI-00001"
    contract_code = models.CharField(max_length=40, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.student} -> {self.cohort} ({self.get_payment_plan_display()})"

    def generate_contract_code(self) -> str:
        """Construit le code contrat à partir de l'année académique, la matière, la modalité/type et l'ID."""
        # Année académique: label sans séparateurs (ex: 2024-2025 -> 20242025)
        year = getattr(self.cohort, 'academic_year', None)
        year_label = getattr(year, 'label', '')
        year_code = ''.join(ch for ch in (year_label or '') if ch.isdigit()) or '00000000'

        # Matière -> JP/CH/KR (fallback: 2 premières lettres en MAJ)
        subj = getattr(self.cohort, 'subject', None)
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

        # Type: P/O (groupe) ou PI/OI (individuel)
        modality = getattr(self.cohort, 'modality', 'IN_PERSON')
        is_individual = getattr(self.cohort, 'is_individual', False)
        if is_individual:
            type_code = 'PI' if modality == 'IN_PERSON' else 'OI'
        else:
            type_code = 'P' if modality == 'IN_PERSON' else 'O'

        seq = f"{self.id:05d}" if self.id else "00000"
        return f"{year_code}-{lang}-{type_code}-{seq}"
    
    @property
    def balance_due(self):
        """Calcul dynamique du reste à payer total"""
        total_paid = sum(p.amount for p in self.payments.all())
        return self.tariff.amount - total_paid

    @property
    def hours_remaining(self):
        """Heures restantes (PACK uniquement)."""
        if self.payment_plan != 'PACK':
            return 0
        remaining = float(self.hours_purchased) - float(self.hours_consumed)
        return round(remaining if remaining > 0 else 0.0, 2)
    
    @property
    def is_standard_tariff(self) -> bool:
        """Retourne True si le tarif appliqué est le tarif standard du groupe"""
        return self.tariff.amount == self.cohort.standard_price
    


class Attendance(models.Model):
    """
    La ligne de présence individuelle.
    """
    STATUS_CHOICES = [
        ('PRESENT', 'Présent'),
        ('ABSENT', 'Absent'),
        ('LATE', 'En Retard'),
        ('EXCUSED', 'Excusé'),
    ]

    session = models.ForeignKey('academics.CourseSession', on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PRESENT')
    
    # --- NOUVEAU CHAMP ---
    # Par défaut True : une séance prévue est due, sauf si l'admin décide le contraire.
    billable = models.BooleanField(default=True, verbose_name="Facturable (Déduire du pack)")
    
    note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        etat = "Facturé" if self.billable else "Offert/Excusé"
        return f"{self.student} - {self.session} ({self.status} - {etat})"


class StudentAnnualFee(models.Model):
    """
    Frais d'inscription annuels par étudiant et année académique.
    Montant par défaut: 1000 DA (indicatif) — l'important est l'état payé ou non.
    """
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='annual_fees')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT, related_name='annual_fees')
    amount = models.IntegerField(default=1000)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('student', 'academic_year')
        verbose_name = "Frais d'inscription annuel"
        verbose_name_plural = "Frais d'inscription annuels"

    def __str__(self):
        state = "Payé" if self.is_paid else "Non payé"
        return f"{self.student} - {self.academic_year.label} ({state})"

    def mark_paid(self, when: timezone.datetime | None = None, amount: int | None = None):
        if when is None:
            when = timezone.now()
        if amount is not None:
            self.amount = amount
        self.is_paid = True
        self.paid_at = when
        self.save()