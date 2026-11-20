"""Números de los reportes. Todo se calcula con las ventas válidas (no anuladas) y en hora local.

- Ventas netas = subtotal (sin propina ni ITBIS, que no son ingreso del negocio).
- Ganancia bruta = ventas netas − costo de lo vendido (costo guardado en cada línea al vender).
- Ganancia neta = ganancia bruta − gastos.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from apps.productos.models import Producto
from apps.ventas.models import LineaVenta, Venta

from .models import Gasto

CERO = Decimal('0')
MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
RANGOS = [('1', 'Hoy'), ('7', 'Últimos 7 días'), ('30', 'Últimos 30 días')]
GRANOS = [('dia', 'Por día'), ('semana', 'Por semana'), ('mes', 'Por mes')]


def _corto(n):
    n = float(n)
    if n >= 1000:
        texto = f'{n / 1000:.0f}' if n >= 10000 else f'{n / 1000:.1f}'
        return texto.replace('.0', '') + 'k'
    return str(round(n))


def _costo(ventas):
    expr = ExpressionWrapper(F('costo') * F('cantidad'), output_field=DecimalField())
    return LineaVenta.objects.filter(venta__in=ventas).aggregate(c=Sum(expr))['c'] or CERO


def _barras(items):
    """items: [{'l': etiqueta, 'v': valor, ...}] → agrega la altura en % para pintar."""
    maximo = max([float(i['v']) for i in items] + [1])
    for i in items:
        i['alto'] = max(1, round(float(i['v']) / maximo * 170))
    return items


def _mes_anterior(d, n):
    y, m = d.year, d.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


def serie_ventas(gran, hoy=None):
    """Ventas netas por día (14), semana (8) o mes (6)."""
    hoy = hoy or timezone.localdate()
    if gran == 'semana':
        lunes = hoy - timedelta(days=hoy.weekday())
        desde = lunes - timedelta(weeks=7)
    elif gran == 'mes':
        desde = _mes_anterior(hoy, 5)
    else:
        desde = hoy - timedelta(days=13)

    por_dia = defaultdict(Decimal)
    for fecha, sub in Venta.objects.filter(anulada=False, fecha__date__gte=desde).values_list('fecha', 'subtotal'):
        por_dia[timezone.localtime(fecha).date()] += sub

    items = []
    if gran == 'semana':
        for i in range(8):
            a = desde + timedelta(weeks=i)
            v = sum((por_dia[a + timedelta(days=k)] for k in range(7)), CERO)
            items.append({'l': f'{a.day}/{a.month}', 'v': v, 'etq': _corto(v), 't': f'Semana del {a:%d/%m}'})
    elif gran == 'mes':
        for i in range(6):
            m = _mes_anterior(hoy, 5 - i)
            v = sum((val for d, val in por_dia.items() if d.year == m.year and d.month == m.month), CERO)
            items.append({'l': MESES[m.month - 1], 'v': v, 'etq': _corto(v), 't': f'{MESES[m.month - 1]} {m.year}'})
    else:
        for i in range(14):
            d = desde + timedelta(days=i)
            v = por_dia[d]
            items.append({'l': f'{d.day}/{d.month}', 'v': v, 'etq': _corto(v), 't': f'{d:%d/%m/%Y}'})
    return _barras(items)


def estadisticas(rango='7', gran='dia', hoy=None):
    hoy = hoy or timezone.localdate()
    dias = int(rango) if rango in dict(RANGOS) else 7
    ventas = Venta.objects.filter(anulada=False, fecha__date__gte=hoy - timedelta(days=dias - 1))
    t = ventas.aggregate(neto=Sum('subtotal'), total=Sum('total'))
    neto = t['neto'] or CERO
    n = ventas.count()
    costo = _costo(ventas)

    # productos (incluye los que no se vendieron, para "menos vendidos")
    vendidos = dict(LineaVenta.objects.filter(venta__in=ventas).values('producto').annotate(q=Sum('cantidad')).values_list('producto', 'q'))
    lista = [{'n': p.nombre, 'q': vendidos.get(p.pk, 0)} for p in Producto.objects.filter(activo=True)]
    mas = sorted(lista, key=lambda x: (-x['q'], x['n']))[:6]
    menos = sorted(lista, key=lambda x: (x['q'], x['n']))[:6]
    maximo = max([x['q'] for x in mas] + [1])
    for x in mas + menos:
        x['porc'] = round(x['q'] / maximo * 100)

    # horas
    horas = [0] * 24
    for fecha in ventas.values_list('fecha', flat=True):
        horas[timezone.localtime(fecha).hour] += 1
    con_ventas = [h for h in range(24) if horas[h]]
    h_min, h_max = (con_ventas[0], con_ventas[-1]) if con_ventas else (17, 23)
    umbral = sorted(horas, reverse=True)[2] or 1
    items_horas = [{'l': f'{h}h', 'v': horas[h], 'etq': horas[h] or '', 'pico': horas[h] >= umbral and horas[h] > 0,
                    't': f'{h}:00 · {horas[h]} ventas'} for h in range(h_min, h_max + 1)]
    pico = max(items_horas, key=lambda x: x['v']) if con_ventas else None

    # métodos de pago
    totales = dict(ventas.values('metodo').annotate(s=Sum('total')).values_list('metodo', 's'))
    total = sum(totales.values(), CERO) or Decimal('1')
    metodos = [{'m': m, 'total': totales.get(m, CERO), 'porc': round(totales.get(m, CERO) / total * 100)} for m in Venta.Metodo.values]

    # meseras (solo ventas de mesa con quién atendió)
    filas = (ventas.exclude(mesera='').values('mesera')
             .annotate(cuentas=Count('pk'), neto=Sum('subtotal'), propina=Sum('propina')).order_by('-neto'))
    tope = max([f['neto'] for f in filas] + [Decimal('1')])
    meseras = [{**f, 'porc': round(f['neto'] / tope * 100)} for f in filas]

    return {
        'neto': neto, 'n': n, 'promedio': neto / n if n else CERO, 'bruta': neto - costo,
        'serie': serie_ventas(gran, hoy), 'mas': mas, 'menos': menos, 'hay_vendidos': bool(mas and mas[0]['q']),
        'horas': _barras(items_horas), 'pico': pico, 'metodos': metodos,
        'meseras': meseras,
    }


def ganancias(anio, mes):
    ventas = Venta.objects.filter(anulada=False, fecha__year=anio, fecha__month=mes)
    t = ventas.aggregate(neto=Sum('subtotal'), propina=Sum('propina'), itbis=Sum('itbis'))
    neto = t['neto'] or CERO
    costo = _costo(ventas)
    bruta = neto - costo
    gastos = Gasto.objects.filter(fecha__year=anio, fecha__month=mes).select_related('usuario')
    total_gastos = gastos.aggregate(s=Sum('monto'))['s'] or CERO
    neta = bruta - total_gastos
    por_cat = list(gastos.values('categoria').annotate(s=Sum('monto')).order_by('-s'))
    maximo = por_cat[0]['s'] if por_cat else 1
    for c in por_cat:
        c['porc'] = round(c['s'] / maximo * 100)
    return {
        'n': ventas.count(), 'neto': neto, 'costo': costo, 'bruta': bruta, 'gastos_total': total_gastos, 'neta': neta,
        'porc_neta': round(neta / neto * 100) if neto else None,
        'propina': t['propina'] or CERO, 'itbis': t['itbis'] or CERO,
        'por_categoria': por_cat, 'gastos': gastos,
    }
