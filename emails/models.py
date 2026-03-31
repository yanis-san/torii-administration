from django.db import models
from core.models import User
from academics.models import Cohort


class EmailCampaign(models.Model):
    """
    Historique des envois d'emails groupés
    """
    RECIPIENT_TYPES = [
        ('COHORT', 'Cohort Spécifique'),
        ('ALL_ACTIVE', 'Tous les Étudiants Actifs'),
        ('ALL_STUDENTS', 'Tous les Étudiants (Actifs + Inactifs)'),
    ]

    title = models.CharField(max_length=200, verbose_name="Titre de la campagne")
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES, verbose_name="Type de destinataires")
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, null=True, blank=True, related_name='email_campaigns', verbose_name="Cohort ciblé")
    
    subject = models.CharField(max_length=255, verbose_name="Objet de l'email")
    message = models.TextField(verbose_name="Message")
    
    # Pièce jointe optionnelle
    attachment = models.FileField(upload_to='email_attachments/', blank=True, null=True, verbose_name="Pièce jointe")
    
    # Métadonnées
    sent_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='email_campaigns_sent', verbose_name="Envoyé par")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    
    # Statistiques
    total_recipients = models.IntegerField(default=0, verbose_name="Nombre de destinataires")
    success_count = models.IntegerField(default=0, verbose_name="Envois réussis")
    failure_count = models.IntegerField(default=0, verbose_name="Envois échoués")
    
    recipient_emails = models.TextField(blank=True, verbose_name="Liste des emails (séparés par virgule)")
    
    # Détails individuels de chaque envoi au format JSON
    # Ex: {"email@example.com": {"status": "success", "sent_at": "2024-01-01 12:00:00"}, ...}
    recipient_details = models.JSONField(default=dict, blank=True, verbose_name="Détails par destinataire")
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Campagne d'Email"
        verbose_name_plural = "Campagnes d'Email"

    def __str__(self):
        return f"{self.title} - {self.get_recipient_type_display()} ({self.sent_at.strftime('%d/%m/%Y')})"
