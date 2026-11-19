from django.contrib import messages
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Greatest
from django.shortcuts import get_object_or_404, redirect, render

from apps.productos.models import Producto
from apps.proveedores.models import Proveedor
from apps.usuarios.permisos import requiere

from .models import Movimiento
from .servicios import MOTIVOS_AJUSTE, InventarioError, ajustar, lista_para_pedir, registrar_entrada


def _controlados():
    return Producto.objects.filter(controla_stock=True, activo=True)


def _resumen():
    c = _controlados()
    valor = c.aggregate(v=Sum(ExpressionWrapper(Greatest(F('stock'), 0) * F('costo'), output_field=DecimalField())))['v']
    return {
        'controlados': c.count(),
        'bajos': c.filter(stock__gt=0, stock__lte=F('stock_minimo')).count(),
        'agotados': c.filter(stock__lte=0).count(),
        'valor': valor or 0,
    }


def _pagina(request, seccion='existencias', modal=None, status=200, **extra):
    ctx = {'seccion': seccion, 'resumen': _resumen(), 'modal': modal}
    if seccion == 'existencias':
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        lista = _controlados().select_related('categoria').annotate(
            valor=ExpressionWrapper(Greatest(F('stock'), 0) * F('costo'), output_field=DecimalField()))
        if q:
            lista = lista.filter(nombre__icontains=q)
        if estado == 'bajo':
            lista = lista.filter(stock__lte=F('stock_minimo'))
        ctx.update(productos=lista.order_by('nombre'), filtros={'q': q, 'estado': estado})
    else:
        q = request.GET.get('q', '').strip()
        tipo = request.GET.get('tipo', '')
        movs = Movimiento.objects.select_related('producto', 'usuario', 'venta', 'proveedor')
        if tipo in Movimiento.Tipo.values:
            movs = movs.filter(tipo=tipo)
        if q:
            movs = movs.filter(Q(producto__nombre__icontains=q) | Q(nota__icontains=q) | Q(proveedor__nombre__icontains=q))
        ctx.update(movimientos=movs[:200], tipos=Movimiento.Tipo.choices, filtros={'q': q, 'tipo': tipo})
    ctx.update(extra)
    return render(request, 'inventario/inicio.html', ctx, status=status)


@requiere('inventario')
def inicio(request):
    return _pagina(request)


@requiere('inventario')
def movimientos(request):
    return _pagina(request, 'movimientos')


@requiere('inventario', 'editar')
def entrada(request):
    datos = request.POST if request.method == 'POST' else {}
    if request.method == 'POST':
        try:
            mov = registrar_entrada(producto_id=datos.get('producto'), cantidad=datos.get('cantidad'),
                                    costo=datos.get('costo'), nota=datos.get('nota', ''), usuario=request.user,
                                    proveedor_id=datos.get('proveedor'))
        except InventarioError as e:
            return _pagina(request, modal='entrada', status=400, error=str(e), datos=datos,
                           opciones=_controlados().order_by('nombre'), proveedores=Proveedor.objects.all())
        messages.success(request, f'Entrada registrada: +{mov.cantidad} {mov.producto.nombre} (ahora {mov.stock_despues})')
        return redirect('inventario:inicio')
    elegido = _controlados().filter(pk=request.GET.get('producto') or 0).first()
    inicial = {'producto': str(elegido.pk), 'costo': elegido.costo} if elegido else {}
    return _pagina(request, modal='entrada', datos=inicial, opciones=_controlados().order_by('nombre'),
                   proveedores=Proveedor.objects.all())


@requiere('inventario', 'editar')
def ajuste(request, pk):
    producto = get_object_or_404(_controlados(), pk=pk)
    if request.method == 'POST':
        try:
            ajustar(producto_id=producto.pk, conteo=request.POST.get('conteo'), motivo=request.POST.get('motivo'),
                    nota=request.POST.get('nota', ''), usuario=request.user)
        except InventarioError as e:
            return _pagina(request, modal='ajuste', status=400, error=str(e), producto=producto,
                           datos=request.POST, motivos=MOTIVOS_AJUSTE)
        messages.success(request, f'Ajuste guardado: {producto.nombre}')
        return redirect('inventario:inicio')
    return _pagina(request, modal='ajuste', producto=producto, datos={'conteo': producto.stock}, motivos=MOTIVOS_AJUSTE)


@requiere('inventario')
def pedir(request):
    return _pagina(request, modal='pedir', pedidos=lista_para_pedir())


@requiere('inventario')
def pedir_imprimir(request):
    return render(request, 'inventario/pedir_imprimir.html', {
        'pedidos': lista_para_pedir(), 'imprimir': request.GET.get('imprimir') == '1',
    })
