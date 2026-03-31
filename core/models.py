from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Utilisateur système (Admin, Staff, Professeur)"""
    is_teacher = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    profile_picture = models.ImageField(
        upload_to='profiles/users/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )

    def save(self, *args, **kwargs):
        from core.image_utils import compress_image
        try:
            this = User.objects.get(id=self.id)
            if this.profile_picture != self.profile_picture:
                self.profile_picture = compress_image(self.profile_picture, max_width=500)
        except User.DoesNotExist:
            if self.profile_picture:
                self.profile_picture = compress_image(self.profile_picture, max_width=500)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

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

class AcademicYear(models.Model):
    """Ex: 2024-2025"""
    label = models.CharField(max_length=20, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    registration_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000,
        verbose_name="Prix des frais d'inscription (DA)"
    )

    def __str__(self): return self.label

    def save(self, *args, **kwargs):
        """Garantit qu'une seule année académique est active à la fois."""
        super_result = super().save(*args, **kwargs)
        if self.is_current:
            AcademicYear.objects.exclude(pk=self.pk).update(is_current=False)
        return super_result

    @classmethod
    def get_current(cls):
        """Renvoie l'année académique active, ou None si aucune."""
        return cls.objects.filter(is_current=True).first()

class Classroom(models.Model):
    name = models.CharField(max_length=50) # Ex: Salle Tokyo
    capacity = models.IntegerField(default=15)

    def __str__(self): return self.name


class TeacherProfile(models.Model):
    """
    Profil financier du professeur.
    Stocke les préférences de paiement et informations bancaires.
    """
    PAYMENT_METHODS = [
        ('CASH', 'Espèces'),
        ('TRANSFER', 'Virement (CCP/RIB)'),
        ('CHECK', 'Chèque'),
    ]
    
    PAYMENT_FREQUENCY = [
        ('MONTHLY', 'Mensuel (à la fin du mois)'),
        ('BY_SESSION', 'Par séance (après chaque classe)'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'is_teacher': True}
    )

    # Préférences de paiement
    preferred_payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default='CASH',
        verbose_name="Méthode de Paiement Préférée"
    )
    
    # Fréquence de paiement
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY,
        default='MONTHLY',
        verbose_name="Fréquence de Paiement"
    )

    # Informations bancaires
    bank_details = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="CCP/RIB",
        help_text="Numéro de compte pour virements"
    )

    # Informations fiscales
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="NIF (Numéro d'Identification Fiscale)",
        help_text="Pour les déclarations fiscales"
    )

    # Notes administratives
    notes = models.TextField(
        blank=True,
        verbose_name="Notes Internes",
        help_text="Informations supplémentaires (contrat, horaires, etc.)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Professeur"
        verbose_name_plural = "Profils Professeurs"

    def __str__(self):
        return f"Profil de {self.user.get_full_name()}"


# Signal pour créer automatiquement le TeacherProfile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_teacher_profile(sender, instance, created, **kwargs):
    """
    Crée automatiquement un TeacherProfile quand un User enseignant est créé.
    """
    if created and instance.is_teacher:
        TeacherProfile.objects.create(user=instance)