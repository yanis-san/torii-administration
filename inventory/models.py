from django.db import models
from django.utils import timezone
from core.models import User


class ItemCategory(models.Model):
    """Catégories d'articles (Fournitures, Équipement, Nettoyage, etc.)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Couleur hex pour le visuel",
        verbose_name="Couleur"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Catégorie d'articles"
        verbose_name_plural = "Catégories d'articles"

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """Articles en inventaire"""
    STATUS_CHOICES = [
        ('in_stock', '✅ En stock'),
        ('low_stock', '⚠️ Stock faible'),
        ('out_of_stock', '❌ Rupture'),
        ('order_pending', '📦 En commande'),
    ]

    name = models.CharField(max_length=200, verbose_name="Nom de l'article")
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT, related_name='items', verbose_name="Catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Quantités
    quantity_current = models.PositiveIntegerField(default=0, verbose_name="Quantité actuelle")
    quantity_min = models.PositiveIntegerField(default=5, verbose_name="Quantité minimale (alerte)")
    unit = models.CharField(max_length=50, default="pièce", verbose_name="Unité (pièce, boîte, pack...)")
    
    # Prix et localisation
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Prix d'achat (€)")
    location = models.CharField(max_length=200, blank=True, verbose_name="Localisation (Bureau, Stockage...)")
    
    # Statut
    is_mandatory = models.BooleanField(default=False, verbose_name="Article obligatoire")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock', verbose_name="Statut")
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = "Article d'inventaire"
        verbose_name_plural = "Articles d'inventaire"

    def __str__(self):
        return f"{self.name} ({self.quantity_current} {self.unit})"
    
    def save(self, *args, **kwargs):
        """Mettre à jour le statut automatiquement"""
        if self.quantity_current == 0:
            self.status = 'out_of_stock'
        elif self.quantity_current <= self.quantity_min:
            self.status = 'low_stock'
        elif self.status != 'order_pending':
            self.status = 'in_stock'
        super().save(*args, **kwargs)


class ShoppingList(models.Model):
    """Listes d'achat pour événements ou besoins spécifiques"""
    STATUS_CHOICES = [
        ('draft', '📝 Brouillon'),
        ('in_progress', '🔄 En cours'),
        ('completed', '✅ Complétée'),
        ('cancelled', '❌ Annulée'),
    ]

    title = models.CharField(max_length=200, verbose_name="Titre de la liste")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Dates
    event_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date de l'événement/besoin",
        help_text="Pour quand est-ce que tu as besoin de ces articles ?"
    )
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    # Status et coût
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Coût total estimé")
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='shopping_lists', verbose_name="Créée par")
    notes = models.TextField(blank=True, verbose_name="Notes globales")
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = "Liste d'achat"
        verbose_name_plural = "Listes d'achat"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def update_total_cost(self):
        """Recalculer le coût total"""
        self.total_cost = sum(
            (item.unit_price or 0) * item.quantity_needed 
            for item in self.items.all()
        )
        self.save(update_fields=['total_cost'])


class ShoppingListItem(models.Model):
    """Articles dans une liste d'achat"""
    PRIORITY_CHOICES = [
        (1, '🔴 Critique (URGENT)'),
        (2, '🟠 Haute'),
        (3, '🟡 Normale'),
        (4, '🔵 Basse'),
        (5, '⚪ Très basse (optionnel)'),
    ]

    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items', verbose_name="Liste d'achat")
    
    # Article : lié à l'inventaire OU créé custom
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_items',
        verbose_name="Article existant"
    )
    custom_item_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nom personnalisé (si article non catalogué)"
    )
    
    # Quantité et prix
    quantity_needed = models.PositiveIntegerField(default=1, verbose_name="Quantité")
    unit = models.CharField(max_length=50, default="pièce", verbose_name="Unité")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Prix unitaire (€)")
    
    # Status d'achat
    is_purchased = models.BooleanField(default=False, verbose_name="Acheté")
    purchase_date = models.DateField(blank=True, null=True, verbose_name="Date d'achat")
    supplier = models.CharField(max_length=200, blank=True, verbose_name="Fournisseur")
    
    # Priorité et notes
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3, verbose_name="Priorité")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Article de liste d'achat"
        verbose_name_plural = "Articles de listes d'achat"

    def __str__(self):
        item_name = self.custom_item_name or (self.item.name if self.item else "Article")
        return f"{item_name} x{self.quantity_needed}"
    
    def get_item_name(self):
        """Retourner le nom de l'article (custom ou existant)"""
        return self.custom_item_name or (self.item.name if self.item else "")
    
    def get_total_price(self):
        """Calculer le prix total pour cet article"""
        if self.unit_price:
            return self.unit_price * self.quantity_needed
        return 0
