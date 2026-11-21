"""Toda subida o bajada de stock pasa por aquí para que quede su movimiento (historial)."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from apps.productos.models import Producto

from .models import Movimiento

MOTIVOS_AJUSTE = ['Conteo físico', 'Merma o rotura', 'Consumo del local', 'Otro']


class InventarioError(Exception):
    """Error que se le puede mostrar al usuario tal cual."""


def mover(producto, cantidad, *, tipo, usuario, nota='', costo=0, venta=None, proveedor=None):
    """Suma (o resta) `cantidad` al stock y guarda el movimiento. Debe llamarse dentro de una transacción."""
    Producto.objects.filter(pk=producto.pk).update(stock=F('stock') + cantidad)
    producto.refresh_from_db(fields=['stock'])
    return Movimiento.objects.create(
        producto=producto, tipo=tipo, cantidad=cantidad, stock_despues=producto.stock,
        costo=costo or 0, nota=(nota or '')[:200], venta=venta, proveedor=proveedor, usuario=usuario,
    )


def _producto_controlado(producto_id):
    p = Producto.objects.select_for_update().filter(pk=producto_id).first()
    if p is None:
        raise InventarioError('Elige un producto.')
    if not p.controla_stock:
        raise InventarioError(f'{p.nombre} no controla inventario.')
    return p


def _entero(valor, mensaje):
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        raise InventarioError(mensaje)


@transaction.atomic
def registrar_entrada(*, producto_id, cantidad, usuario, costo=None, nota='', proveedor_id=None):
    p = _producto_controlado(producto_id)
    cantidad = _entero(cantidad, 'Escribe la cantidad que llegó.')
    if cantidad <= 0:
        raise InventarioError('La cantidad debe ser mayor que cero.')
    try:
        costo = Decimal(str(costo).strip()) if costo not in (None, '') else Decimal('0')
    except InvalidOperation:
        raise InventarioError('Escribe un costo válido.')
    if costo < 0:
        raise InventarioError('El costo no puede ser negativo.')
    proveedor = None
    if proveedor_id not in (None, ''):
        from apps.proveedores.models import Proveedor
        proveedor = Proveedor.objects.filter(pk=proveedor_id).first() if str(proveedor_id).isdigit() else None
        if proveedor is None:
            raise InventarioError('Ese proveedor ya no existe.')
    if costo > 0 and costo != p.costo:
        p.costo = costo
        p.save(update_fields=['costo', 'actualizado'])
        from apps.productos.models import actualizar_costo_combos
        actualizar_costo_combos(p)
    return mover(p, cantidad, tipo=Movimiento.Tipo.ENTRADA, usuario=usuario, nota=nota.strip(), costo=costo, proveedor=proveedor)


@transaction.atomic
def ajustar(*, producto_id, conteo, usuario, motivo='Conteo físico', nota=''):
    p = _producto_controlado(producto_id)
    conteo = _entero(conteo, 'Escribe la cantidad real que hay.')
    if conteo < 0:
        raise InventarioError('El conteo no puede ser negativo.')
    diferencia = conteo - p.stock
    if diferencia == 0:
        raise InventarioError('El conteo es igual al stock del sistema: no hay nada que ajustar.')
    if motivo not in MOTIVOS_AJUSTE:
        motivo = 'Otro'
    texto = motivo + (f': {nota.strip()}' if nota and nota.strip() else '')
    return mover(p, diferencia, tipo=Movimiento.Tipo.AJUSTE, usuario=usuario, nota=texto)


def lista_para_pedir():
    """Productos activos en o bajo el mínimo, con cantidad sugerida (reponer hasta el doble del mínimo)."""
    bajos = Producto.objects.filter(activo=True, controla_stock=True, stock__lte=F('stock_minimo')).order_by('nombre')
    return [{'producto': p, 'pedir': max(1, p.stock_minimo * 2 - max(p.stock, 0))} for p in bajos]
