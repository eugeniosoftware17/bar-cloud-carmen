from decimal import ROUND_HALF_UP, Decimal

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ..dibujos import svg

register = template.Library()


@register.filter
def dinero(valor):
    """1500 → 'RD$ 1,500' (sin decimales, como el diseño)."""
    try:
        n = Decimal(valor or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    except Exception:
        return valor
    return f'RD$ {int(n):,}'


@register.simple_tag
def imagen_producto(p):
    """Foto del producto si tiene; si no, su dibujo."""
    if p.foto:
        return format_html('<img src="{}" alt="" loading="lazy">', p.foto.url)
    return mark_safe(svg(p.dibujo, p.color))


@register.inclusion_tag('productos/_estado.html')
def estado_producto(p):
    return {'p': p}
