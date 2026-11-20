"""Reglas de las mesas: abrir cuenta, agregar o quitar consumos, liberar y cobrar.

Al abrir una cuenta se elige la mesera que la atiende; su nombre queda guardado en la venta.
El stock se descuenta al COBRAR (igual que en Venta directa). Mientras la cuenta está abierta,
lo que ya está pedido en todas las mesas se aparta para no prometer más de lo que hay.
"""

from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from apps.productos.models import Producto
from apps.ventas.servicios import VentaError, registrar_venta

from .models import Consumo, Mesa, Mesera


class MesaError(Exception):
    """Error que se le puede mostrar al cajero tal cual."""


def _mesa(mesa_id):
    mesa = Mesa.objects.select_for_update().filter(pk=mesa_id, activa=True).first()
    if mesa is None:
        raise MesaError('Esa mesa ya no existe.')
    return mesa


def apartado(producto, excepto_mesa=None):
    """Unidades de un producto pedidas en mesas abiertas (sin cobrar)."""
    qs = Consumo.objects.filter(producto=producto, mesa__abierta_en__isnull=False)
    if excepto_mesa is not None:
        qs = qs.exclude(mesa=excepto_mesa)
    return qs.aggregate(n=Sum('cantidad'))['n'] or 0


def elegir_mesera(mesera_id=None, nombre=''):
    """Mesera elegida de la lista, o una nueva escrita a mano (si ya existe con ese nombre, se reutiliza)."""
    nombre = ' '.join(str(nombre or '').split())[:40]
    if nombre:
        mesera = Mesera.objects.filter(nombre__iexact=nombre).first()
        if mesera is None:
            return Mesera.objects.create(nombre=nombre)
        if not mesera.activa:
            mesera.activa = True
            mesera.save(update_fields=['activa'])
        return mesera
    try:
        mesera = Mesera.objects.filter(pk=int(mesera_id), activa=True).first()
    except (TypeError, ValueError):
        mesera = None
    if mesera is None:
        raise MesaError('Elige quién va a atender la mesa.')
    return mesera


@transaction.atomic
def abrir(mesa_id, *, usuario, mesera_id=None, nombre=''):
    mesa = _mesa(mesa_id)
    if mesa.ocupada:
        raise MesaError(f'{mesa.nombre} ya tiene la cuenta abierta.')
    mesa.mesera = elegir_mesera(mesera_id, nombre)
    mesa.abierta_en = timezone.now()
    mesa.abierta_por = usuario
    mesa.save(update_fields=['abierta_en', 'abierta_por', 'mesera'])
    return mesa


@transaction.atomic
def cambiar_mesera(mesa_id, *, mesera_id=None, nombre=''):
    mesa = _mesa(mesa_id)
    if not mesa.ocupada:
        raise MesaError('Primero abre la cuenta.')
    mesa.mesera = elegir_mesera(mesera_id, nombre)
    mesa.save(update_fields=['mesera'])
    return mesa


def quitar_mesera(mesera_id):
    """La saca de la lista (las mesas que ya atiende y las ventas guardadas no cambian)."""
    Mesera.objects.filter(pk=mesera_id).update(activa=False)


@transaction.atomic
def cambiar_consumo(mesa_id, producto_id, delta, *, usuario):
    mesa = _mesa(mesa_id)
    try:
        delta = int(delta)
    except (TypeError, ValueError):
        raise MesaError('Cantidad inválida.')
    if delta == 0:
        return mesa
    producto = Producto.objects.select_for_update().filter(pk=producto_id).first()
    if producto is None:
        raise MesaError('Ese producto ya no existe.')
    consumo = Consumo.objects.filter(mesa=mesa, producto=producto).first()
    actual = consumo.cantidad if consumo else 0
    nuevo = actual + delta

    if delta > 0:
        if not producto.activo:
            raise MesaError(f'{producto.nombre} está desactivado.')
        if producto.controla_stock:
            libre = producto.stock - apartado(producto, excepto_mesa=mesa)
            if nuevo > libre:
                if libre <= 0:
                    raise MesaError(f'{producto.nombre}: agotado (o ya pedido en otras mesas).')
                raise MesaError(f'Solo quedan {libre} de {producto.nombre}.')
        if not mesa.ocupada:
            raise MesaError('Primero abre la cuenta y elige quién atiende.')

    if nuevo <= 0:
        if consumo:
            consumo.delete()
    elif consumo:
        consumo.cantidad = nuevo
        consumo.save(update_fields=['cantidad'])
    else:
        Consumo.objects.create(mesa=mesa, producto=producto, cantidad=nuevo)
    return mesa


@transaction.atomic
def liberar(mesa_id):
    """Descarta los consumos sin cobrarlos y deja la mesa libre."""
    mesa = _mesa(mesa_id)
    mesa.consumos.all().delete()
    mesa.abierta_en = None
    mesa.abierta_por = None
    mesa.mesera = None
    mesa.save(update_fields=['abierta_en', 'abierta_por', 'mesera'])
    return mesa


@transaction.atomic
def cobrar(mesa_id, *, usuario, metodo, recibido=None, referencia=''):
    mesa = _mesa(mesa_id)
    lineas = [{'id': c.producto_id, 'cantidad': c.cantidad} for c in mesa.consumos.all()]
    if not lineas:
        raise MesaError('La mesa no tiene consumos.')
    try:
        venta, alertas = registrar_venta(usuario=usuario, lineas=lineas, metodo=metodo,
                                         recibido=recibido, referencia=referencia, mesa=mesa.nombre,
                                         mesera=mesa.mesera.nombre if mesa.mesera else '')
    except VentaError as e:
        raise MesaError(str(e))
    mesa.consumos.all().delete()
    mesa.abierta_en = None
    mesa.abierta_por = None
    mesa.mesera = None
    mesa.save(update_fields=['abierta_en', 'abierta_por', 'mesera'])
    return venta, alertas


def nueva_mesa():
    ultimo = Mesa.objects.aggregate(o=Max('orden'))['o'] or 0
    n = Mesa.objects.count() + 1
    while Mesa.objects.filter(nombre=f'Mesa {n}').exists():
        n += 1
    return Mesa.objects.create(nombre=f'Mesa {n}', orden=ultimo + 1)
