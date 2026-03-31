from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplier deux nombres"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Diviser deux nombres"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
@register.filter
def payment_total(payments):
    """Calculer le total des paiements"""
    try:
        return sum(p.amount for p in payments)
    except (ValueError, TypeError, AttributeError):
        return 0