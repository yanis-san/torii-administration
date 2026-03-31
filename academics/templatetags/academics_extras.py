from django import template
from academics.models import Cohort

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.simple_tag
def get_all_cohorts():
    """Retourne tous les cohorts triés par nom"""
    return Cohort.objects.select_related('subject', 'level', 'teacher').order_by('name')