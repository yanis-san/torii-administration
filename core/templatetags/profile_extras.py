from django import template

register = template.Library()

@register.filter
def get_initials(user):
    """
    Retourne les initiales d'un utilisateur (ex: John Doe -> JD)
    """
    if not user:
        return "?"

    first = user.first_name[:1].upper() if user.first_name else ""
    last = user.last_name[:1].upper() if user.last_name else ""

    if first or last:
        return f"{first}{last}"
    return user.username[:2].upper()


@register.filter
def student_initials(student):
    """
    Retourne les initiales d'un étudiant
    """
    if not student:
        return "?"

    first = student.first_name[:1].upper() if student.first_name else ""
    last = student.last_name[:1].upper() if student.last_name else ""

    return f"{first}{last}" if (first or last) else "??"
