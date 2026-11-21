"""Reglas de negocio de las ventas: calcular totales, registrar (descontando stock) y anular (devolviéndolo).

Los precios y totales SIEMPRE se calculan aquí, en el servidor; lo que manda el navegador
solo dice qué productos y cuántos.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.configuracion.models import Configuracion
from apps.inventario.models import Movimiento
from apps.inventario.servicios import mover
from apps.productos.models import ComboItem, Producto

from .models import LineaVenta, Venta


class VentaError(Exception):
    """Error que se le puede mostrar al cajero tal cual."""


def _peso(valor):
    return Decimal(valor).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def calcular(subtotal, conf=None):
    """Propina e ITBIS según la Configuración del negocio (si están desactivados, valen 0)."""
    conf = conf or Configuracion.obtener()
    subtotal = Decimal(subtotal)
    propina = _peso(subtotal * conf.tasa_propina)
    itbis = _peso(subtotal * conf.tasa_itbis)
    return {'subtotal': subtotal, 'propina': propina, 'itbis': itbis, 'total': subtotal + propina + itbis}


def _limpiar_lineas(lineas):
    """[{'id': 3, 'cantidad': 2}, …] → {3: 2, …} sumando repetidos y validando."""
    cantidades = {}
    for linea in lineas or []:
        try:
            pid, cant = int(linea['id']), int(linea['cantidad'])
        except (KeyError, TypeError, ValueError):
            raise VentaError('La cuenta tiene datos inválidos. Recarga la página.')
        if cant <= 0:
            raise VentaError('Las cantidades deben ser mayores que cero.')
        cantidades[pid] = cantidades.get(pid, 0) + cant
    if not cantidades:
        raise VentaError('La cuenta está vacía.')
    return cantidades


@transaction.atomic
def registrar_venta(*, usuario, lineas, metodo, recibido=None, referencia='', mesa='', mesera=''):
    if metodo not in Venta.Metodo.values:
        raise VentaError('Elige un método de pago válido.')
    cantidades = _limpiar_lineas(lineas)

    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=cantidades, activo=True)}
    faltan = set(cantidades) - set(productos)
    if faltan:
        raise VentaError('Uno de los productos ya no está disponible. Recarga la página.')

    # Los combos se cambian por los productos que los forman: eso es lo que sale del inventario.
    recetas = {}
    for item in ComboItem.objects.filter(combo_id__in=[p.pk for p in productos.values() if p.es_combo]):
        recetas.setdefault(item.combo_id, []).append(item)
    for p in productos.values():
        if p.es_combo and p.pk not in recetas:
            raise VentaError(f'El combo {p.nombre} no tiene productos. Agrégalos en Productos.')
    salen, en_combo = {}, {}  # producto base → unidades; producto base → nombres de los combos que lo usan
    for pid, cant in cantidades.items():
        p = productos[pid]
        if p.es_combo:
            for item in recetas[pid]:
                salen[item.producto_id] = salen.get(item.producto_id, 0) + item.cantidad * cant
                en_combo.setdefault(item.producto_id, []).append(p.nombre)
        else:
            salen[pid] = salen.get(pid, 0) + cant
    base = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=salen)}

    for pid, cant in salen.items():
        p = base[pid]
        if p.controla_stock and cant > p.stock:
            if pid in en_combo:
                raise VentaError(f'No alcanza {p.nombre} para el combo {en_combo[pid][0]}: '
                                 + ('está agotado.' if p.stock <= 0 else f'solo quedan {p.stock}.'))
            raise VentaError(f'{p.nombre}: agotado.' if p.stock <= 0 else f'Solo quedan {p.stock} de {p.nombre}.')

    def costo_de(p):
        if p.es_combo:
            return sum((base[i.producto_id].costo * i.cantidad for i in recetas[p.pk]), Decimal('0'))
        return p.costo

    subtotal = sum((productos[pid].precio * cant for pid, cant in cantidades.items()), Decimal('0'))
    t = calcular(subtotal)

    if metodo == Venta.Metodo.EFECTIVO:
        try:
            recibido = Decimal(str(recibido))
        except Exception:
            raise VentaError('Escribe el monto recibido.')
        if recibido < t['total']:
            raise VentaError('El monto recibido es menor que el total.')
        cambio = recibido - t['total']
    else:
        recibido, cambio = t['total'], Decimal('0')

    venta = Venta.objects.create(
        usuario=usuario, metodo=metodo, mesa=mesa, mesera=(mesera or '')[:40], referencia=(referencia or '').strip()[:60],
        recibido=recibido, cambio=cambio, **t,
    )
    LineaVenta.objects.bulk_create([
        LineaVenta(venta=venta, producto=productos[pid], nombre=productos[pid].nombre,
                   cantidad=cant, precio=productos[pid].precio, costo=costo_de(productos[pid]))
        for pid, cant in cantidades.items()
    ])

    alertas = []
    for pid, cant in salen.items():
        p = base[pid]
        if p.controla_stock:
            nota = f'Venta #{venta.numero}'
            if pid in en_combo:
                nota += ' · Combo: ' + ', '.join(dict.fromkeys(en_combo[pid]))
            mover(p, -cant, tipo=Movimiento.Tipo.VENTA, usuario=usuario, venta=venta, nota=nota)
            if p.stock <= p.stock_minimo:
                alertas.append(p)
    return venta, alertas


@transaction.atomic
def anular_venta(venta, *, usuario, motivo):
    venta = Venta.objects.select_for_update().get(pk=venta.pk)
    motivo = (motivo or '').strip()
    if venta.anulada:
        raise VentaError('Esta venta ya estaba anulada.')
    if not motivo:
        raise VentaError('Escribe el motivo.')
    # Se devuelve exactamente lo que salió (incluye los productos de los combos, aunque el combo haya cambiado después).
    for mov in venta.movimientos.filter(tipo=Movimiento.Tipo.VENTA).select_related('producto').order_by('pk'):
        mover(mov.producto, -mov.cantidad, tipo=Movimiento.Tipo.ANULACION, usuario=usuario, venta=venta,
              nota=f'Anulación venta #{venta.numero}')
    venta.anulada = True
    venta.motivo_anulacion = motivo[:200]
    venta.anulada_por = usuario
    venta.anulada_en = timezone.now()
    venta.save(update_fields=['anulada', 'motivo_anulacion', 'anulada_por', 'anulada_en'])
    return venta
