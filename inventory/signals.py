from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import InventoryItem, ShoppingListItem, ShoppingList


@receiver(post_save, sender=ShoppingListItem)
def update_shopping_list_cost(sender, instance, created, update_fields, **kwargs):
    """Mettre à jour le coût total de la liste quand un article change"""
    if update_fields is None or 'unit_price' in update_fields or 'quantity_needed' in update_fields:
        instance.shopping_list.update_total_cost()


@receiver(post_delete, sender=ShoppingListItem)
def update_shopping_list_cost_on_delete(sender, instance, **kwargs):
    """Mettre à jour le coût total quand un article est supprimé"""
    instance.shopping_list.update_total_cost()


@receiver(post_save, sender=ShoppingList)
def log_shopping_list_creation(sender, instance, created, **kwargs):
    """Log quand une nouvelle liste est créée"""
    if created:
        print(f"📋 Nouvelle liste créée: {instance.title} par {instance.created_by.first_name}")
