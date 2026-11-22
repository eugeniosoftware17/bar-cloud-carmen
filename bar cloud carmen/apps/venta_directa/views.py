from decimal import Decimal
from types import SimpleNamespace

from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.productos.models import Categoria, Producto
from apps.usuarios.permisos import requiere
from apps.ventas.servicios import calcular


@requiere('venta_directa')
def inicio(request):
    categorias = list(Categoria.objects.all())
    productos = Producto.objects.filter(activo=True).select_related('categoria').prefetch_related('componentes__producto')
    return render(request, 'venta_directa/inicio.html', {
        'categorias': categorias,
        'productos': productos,
        'categoria_inicial': categorias[0].pk if categorias else None,
    })


@xframe_options_sameorigin  # se imprime desde un marco escondido en la misma página
@requiere('venta_directa')
def precuenta(request):
    """Pre-cuenta de lo que está en pantalla (?p=id:cantidad,id:cantidad). Usa el mismo diseño que el recibo."""
    pedidos = {}
    for parte in request.GET.get('p', '').split(','):
        pid, _, cant = parte.partition(':')
        if pid.isdigit() and cant.isdigit() and int(cant) > 0:
            pedidos[int(pid)] = pedidos.get(int(pid), 0) + int(cant)
    productos = Producto.objects.in_bulk(list(pedidos))
    lineas = [SimpleNamespace(producto=productos[pid], cantidad=cant, importe=productos[pid].precio * cant)
              for pid, cant in pedidos.items() if pid in productos]
    return render(request, 'mesas/precuenta.html', {
        'cuenta': {
            'mesa': SimpleNamespace(nombre='Venta directa', mesera=None),
            'lineas': lineas,
            't': calcular(sum((l.importe for l in lineas), Decimal('0'))),
        },
        'imprimir': request.GET.get('imprimir') == '1',
    })
