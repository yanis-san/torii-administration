from django import template

register = template.Library()

@register.filter
def key(dictionary, key_name):
    """Accéder à une clé de dictionnaire dans un template"""
    if dictionary and key_name:
        return dictionary.get(key_name, [])
    return []
