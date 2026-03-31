# finance/models.py
from django.db import models
from core.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Tariff(models.Model):
    """
    Le Catalogue des Prix.
    On ne saisit pas le prix à la main à chaque élève. On choisit un tarif.
    Ex: "Tarif 2025 - Japonais N1 - Standard" = 30 000 DA
    Ex: "Tarif 2025 - Japonais N1 - Ancien Élève" = 25 000 DA
    """
    name = models.CharField(max_length=150)
    amount = models.IntegerField(verbose_name="Montant Total (DA)")

    # Optionnel : Lier ce tarif à un type de cours spécifique pour filtrer les listes
    # linked_course_type = models.ForeignKey(...)

    def __str__(self):
        return f"{self.name} ({self.amount:,} DA)".replace(',', ' ')

class Payment(models.Model):
    """
    L'argent qui rentre réellement dans la caisse.
    """
    METHODS = [
        ('CASH', 'Espèces'),
        ('CARD', 'Virement/Carte'),
        ('CHECK', 'Chèque'),
    ]

    # On utilise une chaîne de caractères ('students.Enrollment') pour éviter les imports circulaires
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE, related_name='payments')

    amount = models.IntegerField(verbose_name="Montant (DA)")
    method = models.CharField(max_length=10, choices=METHODS, default='CASH')
    date = models.DateField(verbose_name="Date de paiement", default=timezone.now, help_text="Laissez vide pour utiliser la date d'aujourd'hui")
    transaction_id = models.CharField(max_length=100, blank=True, help_text="Numéro de chèque ou virement")

    # Reçu / Justificatif (PDF, image)
    receipt = models.FileField(
        upload_to='payment_receipts/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Reçu/Justificatif",
        help_text="PDF, image (JPEG, PNG, WEBP)"
    )

    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        from core.image_utils import compress_image
        # Check if receipt is an image
        if self.receipt and hasattr(self.receipt, 'name'):
            ext = self.receipt.name.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                try:
                    this = Payment.objects.get(id=self.id)
                    if this.receipt != self.receipt:
                        self.receipt = compress_image(self.receipt, max_width=1200)
                except Payment.DoesNotExist:
                    self.receipt = compress_image(self.receipt, max_width=1200)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.amount:,} DA - {self.enrollment}".replace(',', ' ')

class Installment(models.Model):
    """
    Les Échéances (Ce que l'élève DOIT payer et QUAND).
    Généré automatiquement selon le plan de paiement choisi.
    """
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE, related_name='installments')
    due_date = models.DateField(verbose_name="Date d'échéance")
    amount = models.IntegerField(verbose_name="Montant dû (DA)")

    is_paid = models.BooleanField(default=False)

    # Lien vers le paiement qui a soldé cette échéance (optionnel, pour traçabilité)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='covered_installments')

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        status = "PAYÉ" if self.is_paid else "IMPAYÉ"
        return f"{self.due_date} : {self.amount:,} DA ({status})".replace(',', ' ')
    


class Discount(models.Model):
    """
    Gestion des promotions (individuelles ou groupe).
    Ex: "Réduction Fratrie (-10%)" ou "Bourse (-5000 DA)"
    """
    TYPES = [
        ('PERCENT', 'Pourcentage (%)'),
        ('FIXED', 'Montant Fixe (DA)'),
    ]

    name = models.CharField(max_length=100) # Ex: Promo Ouverture
    value = models.IntegerField(verbose_name="Valeur")
    type = models.CharField(max_length=10, choices=TYPES, default='FIXED')

    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.type == 'PERCENT':
            return f"{self.name} (-{self.value}%)"
        else:
            return f"{self.name} (-{self.value:,} DA)".replace(',', ' ')


class TeacherPayment(models.Model):
    """
    Historique des paiements aux professeurs (Sorties d'argent).
    Enregistre chaque versement de salaire avec la période couverte.
    """
    PAYMENT_METHODS = [
        ('CASH', 'Espèces'),
        ('TRANSFER', 'Virement (CCP/RIB)'),
        ('CHECK', 'Chèque'),
    ]

    # Professeur concerné
    teacher = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        limit_choices_to={'is_teacher': True},
        related_name='salary_payments',
        verbose_name="Professeur"
    )

    # Période couverte par ce paiement
    period_start = models.DateField(verbose_name="Début de Période")
    period_end = models.DateField(verbose_name="Fin de Période")

    # Montant et méthode
    total_amount = models.IntegerField(
        verbose_name="Montant Total Payé (DA)"
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        verbose_name="Méthode de Paiement"
    )

    # Métadonnées
    payment_date = models.DateField(
        verbose_name="Date de Paiement",
        help_text="Date à laquelle le paiement a été effectué"
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='teacher_payments_recorded',
        verbose_name="Enregistré par"
    )

    # Justificatifs et notes
    proof_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence",
        help_text="N° de chèque, référence virement, etc."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Informations complémentaires sur ce paiement"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Paiement Professeur"
        verbose_name_plural = "Paiements Professeurs"

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.total_amount:,} DA ({self.payment_date})".replace(',', ' ')


class TeacherCohortPayment(models.Model):
    """
    Paiement pour un prof pour UN COHORT SPÉCIFIQUE.
    Permet un suivi détaillé par groupe avec calcul automatique des montants dûs.
    """
    PAYMENT_METHODS = [
        ('CASH', 'Espèces'),
        ('TRANSFER', 'Virement (CCP/RIB)'),
        ('CHECK', 'Chèque'),
    ]

    # Références
    teacher = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        limit_choices_to={'is_teacher': True},
        related_name='cohort_payments',
        verbose_name="Professeur"
    )
    
    cohort = models.ForeignKey(
        'academics.Cohort',
        on_delete=models.PROTECT,
        related_name='teacher_payments',
        verbose_name="Cohort/Groupe"
    )

    # Période
    period_start = models.DateField(verbose_name="Début de Période")
    period_end = models.DateField(verbose_name="Fin de Période")

    # Montants
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant Dû (DA)",
        help_text="Calculé automatiquement: Σ(durée_séance × tarif_horaire)"
    )
    
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant Payé (DA)"
    )

    # Paiement
    payment_date = models.DateField(verbose_name="Date de Paiement")
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        verbose_name="Méthode de Paiement"
    )

    # Métadonnées
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cohort_payments_recorded',
        verbose_name="Enregistré par"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date']
        verbose_name = "Paiement Professeur par Cohort"
        verbose_name_plural = "Paiements Professeurs par Cohort"
        # Indices pour les requêtes fréquentes
        indexes = [
            models.Index(fields=['teacher', 'cohort', '-payment_date']),
            models.Index(fields=['cohort', '-payment_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'cohort', 'period_start', 'period_end', 'payment_date', 'amount_paid'],
                name='unique_cohort_payment_entry'
            )
        ]

    def __str__(self):
        balance = self.amount_due - self.amount_paid
        status = "✓ Soldé" if balance == 0 else f"Reste: {balance} DA"
        return f"{self.teacher.get_full_name()} - {self.cohort.name} - {status}"

    @property
    def balance_due(self):
        """Montant encore dû"""
        return self.amount_due - self.amount_paid

    @property
    def is_fully_paid(self):
        """Vrai si entièrement payé"""
        return self.balance_due == 0