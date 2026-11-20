import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.productos.models import Categoria, Producto
from apps.usuarios.permisos import requiere
from apps.ventas.servicios import calcular
from apps.ventas.views import respuesta_venta

from . import servicios
from .models import Mesa, Mesera
from .servicios import MesaError


def _mesas():
    mesas = list(Mesa.objects.filter(activa=True).select_related('mesera').prefetch_related('consumos__producto'))
    for m in mesas:
        consumos = list(m.consumos.all())
        m.n_productos = len(consumos)
        m.total = calcular(sum((c.importe for c in consumos), Decimal('0')))['total'] if consumos else 0
    return mesas


def _cuenta(mesa):
    if mesa is None:
        return None
    lineas = list(mesa.consumos.select_related('producto').order_by('pk'))
    t = calcular(sum((c.importe for c in lineas), Decimal('0')))
    return {'mesa': mesa, 'lineas': lineas, 't': t}


def _fragmentos(request, mesa_id):
    mesa = Mesa.objects.filter(pk=mesa_id, activa=True).select_related('abierta_por', 'mesera').first() if mesa_id else None
    mesas = _mesas()
    ctx = {'mesas': mesas, 'sel': mesa.pk if mesa else None, 'cuenta': _cuenta(mesa)}
    en_cuenta = {c.producto_id: c.cantidad for c in mesa.consumos.all()} if mesa else {}
    return {
        'grid': render_to_string('mesas/_grid.html', ctx, request=request),
        'cuenta': render_to_string('mesas/_cuenta.html', ctx, request=request),
        'libres': sum(1 for m in mesas if not m.ocupada),
        'ocupadas': sum(1 for m in mesas if m.ocupada),
        'en_cuenta': {str(k): v for k, v in en_cuenta.items()},
        'meseras': [{'id': m.pk, 'nombre': m.nombre} for m in Mesera.objects.filter(activa=True)],
        'mesera': mesa.mesera_id if mesa and mesa.ocupada else None,
    }


def _datos(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return {}


@requiere('mesas')
def inicio(request):
    sel = request.GET.get('mesa')
    sel = int(sel) if sel and sel.isdigit() else None
    frag = _fragmentos(request, sel)
    categorias = list(Categoria.objects.all())
    return render(request, 'mesas/inicio.html', {
        'frag': frag,
        'en_cuenta_json': json.dumps(frag['en_cuenta']),
        'meseras_json': json.dumps(frag['meseras']),
        'sel': sel,
        'categorias': categorias,
        'categoria_inicial': categorias[0].pk if categorias else None,
        'productos': Producto.objects.filter(activo=True).select_related('categoria'),
    })


@requiere('mesas')
def estado(request):
    sel = request.GET.get('mesa')
    return JsonResponse({'ok': True, **_fragmentos(request, int(sel) if sel and sel.isdigit() else None)})


def _accion(request, pk, fn):
    try:
        fn()
    except MesaError as e:
        return JsonResponse({'ok': False, 'error': str(e), **_fragmentos(request, pk)}, status=400)
    return JsonResponse({'ok': True, **_fragmentos(request, pk)})


@requiere('mesas', 'editar')
@require_POST
def abrir(request, pk):
    d = _datos(request)
    return _accion(request, pk, lambda: servicios.abrir(pk, usuario=request.user,
                                                        mesera_id=d.get('mesera'), nombre=d.get('nombre', '')))


@requiere('mesas', 'editar')
@require_POST
def mesera(request, pk):
    d = _datos(request)
    return _accion(request, pk, lambda: servicios.cambiar_mesera(pk, mesera_id=d.get('mesera'), nombre=d.get('nombre', '')))


@requiere('mesas', 'editar')
@require_POST
def quitar_mesera(request, mesera_id):
    servicios.quitar_mesera(mesera_id)
    sel = request.GET.get('mesa')
    return JsonResponse({'ok': True, **_fragmentos(request, int(sel) if sel and sel.isdigit() else None)})


@requiere('mesas', 'editar')
@require_POST
def consumo(request, pk):
    d = _datos(request)
    return _accion(request, pk, lambda: servicios.cambiar_consumo(pk, d.get('producto'), d.get('delta', 1), usuario=request.user))


@requiere('mesas', 'editar')
@require_POST
def liberar(request, pk):
    return _accion(request, pk, lambda: servicios.liberar(pk))


@requiere('mesas', 'editar')
@require_POST
def cobrar(request, pk):
    d = _datos(request)
    try:
        venta, alertas = servicios.cobrar(pk, usuario=request.user, metodo=d.get('metodo'),
                                          recibido=d.get('recibido'), referencia=d.get('referencia', ''))
    except MesaError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({**respuesta_venta(venta, alertas), **_fragmentos(request, pk)})


@requiere('mesas', 'editar')
@require_POST
def nueva(request):
    mesa = servicios.nueva_mesa()
    return JsonResponse({'ok': True, 'nombre': mesa.nombre, **_fragmentos(request, mesa.pk)})


@xframe_options_sameorigin  # se imprime desde un marco escondido en la misma página
@requiere('mesas')
def precuenta(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    return render(request, 'mesas/precuenta.html', {
        'cuenta': _cuenta(mesa), 'imprimir': request.GET.get('imprimir') == '1',
    })
