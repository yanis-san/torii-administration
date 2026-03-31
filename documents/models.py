from django.db import models
from django.conf import settings
import json

class SyncLog(models.Model):
    """Historique des synchronisations"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Stats brutes (JSON)
    stats_json = models.JSONField(default=dict, blank=True)
    
    # Résumé texte
    summary = models.TextField(blank=True)
    
    # Erreurs
    error_count = models.IntegerField(default=0)
    errors_json = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
    
    def __str__(self):
        return f"Sync {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def total_items_processed(self):
        """Total d'items traités"""
        if not self.stats_json:
            return 0
        total = 0
        for key in self.stats_json:
            if key.endswith('_added') or key.endswith('_updated') or key.endswith('_deleted'):
                total += self.stats_json.get(key, 0)
        return total
