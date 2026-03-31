from django.db import models
from django.contrib.auth import get_user_model
from students.models import Student
from prospects.models import Prospect

User = get_user_model()


class Category(models.Model):
    """
    Catégories pour organiser les tâches
    """
    name = models.CharField("Nom", max_length=100, unique=True)
    color = models.CharField("Couleur (hex)", max_length=7, default="#6366F1", help_text="Ex: #6366F1")
    description = models.TextField("Description", blank=True, null=True)
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
    
    def __str__(self):
        return self.name


class Task(models.Model):
    """
    Modèle pour gérer les tâches/to-do avec possibilité de lier à un étudiant, prospect ou personne externe
    """
    PRIORITY_CHOICES = [
        ('LOW', 'Basse'),
        ('MEDIUM', 'Moyenne'),
        ('HIGH', 'Haute'),
        ('URGENT', 'Urgente'),
    ]
    
    # Information de la tâche
    title = models.CharField("Titre", max_length=200)
    description = models.TextField("Description", blank=True, null=True)
    priority = models.CharField("Priorité", max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    
    # Catégorie
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name="Catégorie"
    )
    
    # Dates
    created_at = models.DateTimeField("Date de création", auto_now_add=True)
    scheduled_date = models.DateField("Date planifiée", null=True, blank=True, help_text="Date à laquelle cette tâche doit être faite")
    deadline = models.DateField("Date limite", null=True, blank=True, help_text="Date limite absolue")
    completed_at = models.DateTimeField("Date de complétion", null=True, blank=True)
    
    # Statut
    is_completed = models.BooleanField("Terminée", default=False)
    
    # Relations optionnelles
    student = models.ForeignKey(
        Student, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks',
        verbose_name="Étudiant"
    )
    
    prospect = models.ForeignKey(
        Prospect, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks',
        verbose_name="Prospect"
    )
    
    # Pour les personnes non enregistrées (backup si pas de student/prospect)
    external_person_name = models.CharField("Nom personne externe", max_length=200, blank=True, null=True)
    external_person_phone = models.CharField("Téléphone personne externe", max_length=20, blank=True, null=True)
    
    # Créateur de la tâche
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_tasks',
        verbose_name="Créée par"
    )
        # Utilisateur assigné à la tâche
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Assigné à"
    )
        # Notes additionnelles
    notes = models.TextField("Notes", blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"
    
    def __str__(self):
        status = "✓" if self.is_completed else "○"
        person = self.get_related_person_display()
        return f"{status} {self.title} - {person}" if person else f"{status} {self.title}"
    
    def get_related_person_display(self):
        """Retourne le nom de la personne liée à la tâche"""
        if self.student:
            return f"{self.student.first_name} {self.student.last_name}".strip()
        elif self.prospect:
            return f"{self.prospect.first_name} {self.prospect.last_name}".strip()
        elif self.external_person_name:
            return self.external_person_name
        return None
    
    def get_related_person_phone(self):
        """Retourne le téléphone de la personne liée"""
        if self.student:
            return self.student.phone
        elif self.prospect:
            return self.prospect.phone
        elif self.external_person_phone:
            return self.external_person_phone
        return None
    
    def mark_completed(self):
        """Marquer la tâche comme terminée"""
        from django.utils import timezone
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()
    
    def mark_incomplete(self):
        """Marquer la tâche comme non terminée"""
        self.is_completed = False
        self.completed_at = None
        self.save()
