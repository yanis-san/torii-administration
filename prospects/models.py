from django.db import models
from django.utils import timezone
import json


class Prospect(models.Model):
    """Prospects venant du formulaire de contact du site"""
    
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name="Âge")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    level = models.CharField(max_length=50, blank=True, verbose_name="Niveau")
    source = models.CharField(max_length=100, blank=True, verbose_name="Source")
    activity_type = models.CharField(max_length=200, blank=True, verbose_name="Type d'activité")
    specific_course = models.CharField(max_length=200, blank=True, verbose_name="Cours spécifique")
    message = models.TextField(blank=True, verbose_name="Message")
    notes = models.TextField(blank=True, verbose_name="Notes")
    converted = models.BooleanField(default=False, verbose_name="Converti")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        verbose_name = "Prospect"
        verbose_name_plural = "Prospects"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_activity_summary(self):
        """Retourne un résumé des intérêts"""
        parts = []
        if self.activity_type:
            parts.append(self.activity_type)
        if self.specific_course:
            parts.append(self.specific_course)
        return " - ".join(parts) if parts else "Non spécifié"


class UploadHistory(models.Model):
    """Historique des imports CSV de prospects"""
    
    filename = models.CharField(max_length=255, verbose_name="Nom du fichier")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'import")
    
    # Résumé de l'import
    total_processed = models.IntegerField(verbose_name="Total traité")
    created_count = models.IntegerField(verbose_name="Créés")
    updated_count = models.IntegerField(verbose_name="Fusionnés")
    
    # Détails en JSON pour plus de flexibilité
    created_data = models.JSONField(default=list, verbose_name="Prospects créés")
    updated_data = models.JSONField(default=list, verbose_name="Prospects fusionnés")
    duplicates_data = models.JSONField(default=list, verbose_name="Doublons détectés")
    errors_data = models.JSONField(default=list, verbose_name="Erreurs")
    
    class Meta:
        verbose_name = "Historique d'import"
        verbose_name_plural = "Historiques d'import"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Import {self.filename} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"
    
    @property
    def created_list(self):
        return self.created_data if isinstance(self.created_data, list) else []
    
    @property
    def updated_list(self):
        return self.updated_data if isinstance(self.updated_data, list) else []
    
    @property
    def duplicates_count(self):
        return len(self.duplicates_data) if isinstance(self.duplicates_data, list) else 0
    
    @property
    def errors_count(self):
        return len(self.errors_data) if isinstance(self.errors_data, list) else 0
