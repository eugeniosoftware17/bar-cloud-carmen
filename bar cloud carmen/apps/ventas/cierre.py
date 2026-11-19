"""Cierre del día: resumen de ventas de una fecha y cuadre de caja."""

from decimal import Decimal, InvalidOperation

from django.db.models import Count, Sum
from django.utils import timezone

from .models import CierreCaja, LineaVenta, Venta
from .servicios import VentaError

CERO = Decimal('0')


def resumen_dia(dia):
    ventas = Venta.objects.filter(fecha__date=dia)
    validas = ventas.filter(anulada=False)
    t = validas.aggregate(n=Count('pk'), total=Sum('total'), neto=Sum('subtotal'), propina=Sum('propina'), itbis=Sum('itbis'))
    anuladas = ventas.filter(anulada=True).aggregate(n=Count('pk'), total=Sum('total'))

    por_metodo = {m: {'metodo': m, 'n': 0, 'total': CERO} for m in Venta.Metodo.values}
    for fila in validas.values('metodo').annotate(n=Count('pk'), total=Sum('total')):
        por_metodo[fila['metodo']].update(n=fila['n'], total=fila['total'])
    total = t['total'] or CERO
    for m in por_metodo.values():
        m['porcentaje'] = round(m['total'] / total * 100) if total else 0

    top = list(LineaVenta.objects.filter(venta__in=validas).values('nombre')
               .annotate(cantidad=Sum('cantidad')).order_by('-cantidad', 'nombre')[:5])
    maximo = top[0]['cantidad'] if top else 1
    for p in top:
        p['porcentaje'] = round(p['cantidad'] / maximo * 100)

    return {
        'dia': dia,
        'num_ventas': t['n'],
        'total': total,
        'neto': t['neto'] or CERO,
        'propina': t['propina'] or CERO,
        'itbis': t['itbis'] or CERO,
        'anuladas_n': anuladas['n'],
        'anuladas_total': anuladas['total'] or CERO,
        'efectivo': por_metodo[Venta.Metodo.EFECTIVO]['total'],
        'por_metodo': list(por_metodo.values()),
        'top': top,
    }


def _monto(valor, nombre):
    try:
        monto = Decimal(str(valor).strip() or '0')
    except (InvalidOperation, ValueError):
        raise VentaError(f'Escribe un número válido en {nombre}.')
    if monto < 0:
        raise VentaError(f'{nombre.capitalize()} no puede ser negativo.')
    return monto


def cerrar_dia(*, dia, fondo, contado, usuario, nota=''):
    if dia > timezone.localdate():
        raise VentaError('No se puede cerrar un día que todavía no llega.')
    if contado is None or str(contado).strip() == '':
        raise VentaError('Escribe el efectivo contado para cerrar el día.')
    fondo = _monto(fondo, 'el fondo inicial')
    contado = _monto(contado, 'el efectivo contado')
    r = resumen_dia(dia)
    esperado = fondo + r['efectivo']
    cierre, _ = CierreCaja.objects.update_or_create(dia=dia, defaults={
        'fondo': fondo, 'ventas_efectivo': r['efectivo'], 'total_vendido': r['total'], 'num_ventas': r['num_ventas'],
        'esperado': esperado, 'contado': contado, 'diferencia': contado - esperado,
        'nota': (nota or '').strip()[:200], 'usuario': usuario,
    })
    return cierre
