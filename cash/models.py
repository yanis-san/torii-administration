from django.db import models
from django.utils import timezone


class CashCategory(models.Model):
    """
    Catégorie de caisse (ex: Monnaie, JLPT, Caisse Principale, etc.)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    current_amount = models.IntegerField(default=0, verbose_name="Montant actuel (DA)")
    created_at = models.DateTimeField(auto_now_add=True)
    last_reset = models.DateTimeField(null=True, blank=True, verbose_name="Dernier reset")
    is_total = models.BooleanField(default=False, verbose_name="Catégorie TOTAL (calculée automatiquement)")
    
    class Meta:
        verbose_name = "Catégorie de caisse"
        verbose_name_plural = "Catégories de caisse"
        ordering = ['-is_total', 'name']  # TOTAL en premier
    
    def __str__(self):
        return f"{self.name} ({self.current_amount:,} DA)".replace(',', ' ')


class CashTransaction(models.Model):
    """
    Transaction manuelle dans une catégorie de caisse
    """
    TRANSACTION_TYPES = [
        ('ADD', 'Ajout (+)'),
        ('REMOVE', 'Retrait (-)'),
        ('SET', 'Définir le montant'),
        ('RESET', 'Reset'),
    ]
    
    category = models.ForeignKey(CashCategory, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='ADD')
    amount = models.IntegerField(verbose_name="Montant (DA)")
    note = models.TextField(blank=True, verbose_name="Note / Raison")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Montant avant et après pour historique
    amount_before = models.IntegerField(verbose_name="Montant avant")
    amount_after = models.IntegerField(verbose_name="Montant après")
    
    class Meta:
        verbose_name = "Transaction de caisse"
        verbose_name_plural = "Transactions de caisse"
        ordering = ['-created_at']
    
    def __str__(self):
        symbol = '+' if self.transaction_type == 'ADD' else '-' if self.transaction_type == 'REMOVE' else '='
        return f"{self.category.name} {symbol}{self.amount:,} DA".replace(',', ' ')
