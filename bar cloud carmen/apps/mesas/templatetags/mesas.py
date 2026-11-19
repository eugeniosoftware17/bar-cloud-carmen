from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def hace(fecha):
    """Tiempo desde que se abrió la cuenta: '25 min' o '1 h 10 min'."""
    if not fecha:
        return ''
    minutos = max(0, int((timezone.now() - fecha).total_seconds() // 60))
    if minutos < 60:
        return f'{minutos} min'
    return f'{minutos // 60} h {minutos % 60} min'
