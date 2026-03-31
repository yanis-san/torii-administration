# core/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='format_da')
def format_da(value):
    """
    Formate un nombre entier avec des espaces comme séparateurs de milliers.
    Ex: 30000 -> "30 000"
    """
    try:
        # Convertir en entier si ce n'est pas déjà le cas
        number = int(value)
        # Formater avec des virgules puis remplacer par des espaces
        formatted = f"{number:,}".replace(',', ' ')
        return formatted
    except (ValueError, TypeError):
        return value
