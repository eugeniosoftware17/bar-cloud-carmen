import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.configuracion.models import Configuracion
from apps.productos.models import Producto
from apps.usuarios.permisos import puede, requiere, requiere_alguno

from .cierre import cerrar_dia, resumen_dia
from .models import CierreCaja, Venta
from .servicios import VentaError, anular_venta, registrar_venta

PERIODOS = [('0', 'Hoy'), ('1', 'Ayer'), ('7', 'Últimos 7 días'), ('30', 'Últimos 30 días'), ('todas', 'Todas')]
ESTADOS = [('', 'Válidas y anuladas'), ('valida', 'Solo válidas'), ('anulada', 'Solo anuladas')]


# ---------- cobrar (Venta directa y, más adelante, Mesas) ----------

@requiere('venta_directa', 'editar')
@require_POST
def cobrar(request):
    try:
        datos = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    try:
        venta, alertas = registrar_venta(
            usuario=request.user,
            lineas=datos.get('lineas'),
            metodo=datos.get('metodo'),
            recibido=datos.get('recibido'),
            referencia=datos.get('referencia', ''),
        )
    except VentaError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse(respuesta_venta(venta, alertas))


def respuesta_venta(venta, alertas):
    """Lo que la ventana de cobro necesita después de cobrar (Venta directa y Mesas)."""
    # stock nuevo de lo que salió del inventario y de los combos que usan esos productos
    movidos = list(Producto.objects.filter(movimientos__venta=venta).distinct())
    stock = {str(p.pk): p.stock for p in movidos}
    for combo in (Producto.objects.filter(es_combo=True, componentes__producto__in=movidos).distinct()
                  .prefetch_related('componentes__producto')):
        stock[str(combo.pk)] = combo.stock_js
    return {
        'ok': True,
        'venta': {
            'id': venta.pk, 'numero': venta.numero, 'metodo': venta.metodo,
            'total': float(venta.total), 'cambio': float(venta.cambio),
        },
        'recibo': reverse('ventas:recibo', args=[venta.pk]),
        'imprimir_auto': Configuracion.obtener().recibo_imprimir_al_cobrar,
        'alertas': [f'{p.nombre} ({p.stock})' for p in alertas],
        'stock': stock,
    }


@xframe_options_sameorigin  # se imprime desde un marco escondido en la misma página
@requiere_alguno('venta_directa', 'mesas', 'ventas')
def recibo(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('usuario').prefetch_related('lineas'), pk=pk)
    conf = Configuracion.obtener()
    dos = conf.recibo_dos_copias and request.GET.get('copias') != '1'
    imprimir = request.GET.get('imprimir') == '1'
    copias = ['COPIA CLIENTE', 'COPIA NEGOCIO'] if dos else ['']
    siguiente = ''
    if dos and conf.recibo_copias_separadas and imprimir:
        # una copia por impresión: primero la del cliente y, al terminar, la del negocio
        if request.GET.get('copia') == '2':
            copias = ['COPIA NEGOCIO']
        else:
            copias = ['COPIA CLIENTE']
            siguiente = reverse('ventas:recibo', args=[venta.pk]) + '?imprimir=1&copia=2'
    return render(request, 'ventas/recibo.html', {
        'venta': venta,
        'copias': copias,
        'dos_copias': dos,
        'separadas': conf.recibo_copias_separadas,
        'imprimir': imprimir,
        'siguiente': siguiente,
    })


# ---------- historial ----------

def _filtrar(request):
    per = request.GET.get('per', '7')
    if per not in dict(PERIODOS):
        per = '7'
    metodo = request.GET.get('metodo', '')
    estado = request.GET.get('estado', '')
    num = request.GET.get('num', '').strip().lstrip('#').lstrip('0')

    ventas = Venta.objects.select_related('usuario')
    hoy = timezone.localdate()
    if per == '0':
        ventas = ventas.filter(fecha__date=hoy)
    elif per == '1':
        ventas = ventas.filter(fecha__date=hoy - timedelta(days=1))
    elif per != 'todas':
        ventas = ventas.filter(fecha__date__gte=hoy - timedelta(days=int(per) - 1))
    if metodo in Venta.Metodo.values:
        ventas = ventas.filter(metodo=metodo)
    if estado == 'valida':
        ventas = ventas.filter(anulada=False)
    elif estado == 'anulada':
        ventas = ventas.filter(anulada=True)
    if num.isdigit():
        ventas = ventas.filter(pk=int(num))
    return ventas, {'per': per, 'metodo': metodo, 'estado': estado, 'num': request.GET.get('num', '')}


def _resumen(ventas):
    validas = ventas.filter(anulada=False).aggregate(n=Count('pk'), total=Sum('total'), neto=Sum('subtotal'), promedio=Avg('subtotal'))
    anuladas = ventas.filter(anulada=True).aggregate(n=Count('pk'), total=Sum('total'))
    return {'validas': validas, 'anuladas': anuladas}


def _pagina(request, venta=None, anular=False, error='', status=200):
    ventas, filtros = _filtrar(request)
    return render(request, 'ventas/inicio.html', {
        'ventas': ventas[:200],
        'resumen': _resumen(ventas),
        'filtros': filtros,
        'periodos': PERIODOS,
        'metodos': Venta.Metodo.values,
        'estados': ESTADOS,
        'venta': venta,
        'anular': anular,
        'error': error,
        'volver': _destino(request),
    }, status=status)


def _destino(request):
    destino = request.POST.get('volver') or request.GET.get('volver') or ''
    return destino if destino.startswith('?') else ''


@requiere('ventas')
def inicio(request):
    return _pagina(request)


@requiere('ventas')
def detalle(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('usuario', 'anulada_por').prefetch_related('lineas'), pk=pk)
    return _pagina(request, venta=venta)


@requiere('ventas', 'editar')
def anular(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('usuario', 'anulada_por').prefetch_related('lineas'), pk=pk)
    if request.method == 'POST':
        try:
            anular_venta(venta, usuario=request.user, motivo=request.POST.get('motivo'))
        except VentaError as e:
            return _pagina(request, venta=venta, anular=True, error=str(e), status=400)
        messages.success(request, f'Venta #{venta.numero} anulada. Los productos volvieron al inventario.')
        return redirect(reverse('ventas:inicio') + _destino(request))
    if venta.anulada:
        return redirect('ventas:detalle', pk=venta.pk)
    return _pagina(request, venta=venta, anular=True)


# ---------- cierre del día ----------

def _dia(request):
    hoy = timezone.localdate()
    texto = request.POST.get('dia') or request.GET.get('dia') or ''
    try:
        dia = date.fromisoformat(texto)
    except ValueError:
        return hoy
    return min(dia, hoy)


@requiere('ventas')
def cierre(request):
    dia = _dia(request)
    error = ''
    if request.method == 'POST':
        if not puede(request.user, 'ventas', 'editar'):
            return render(request, 'bloqueo.html', {'solo_ver': True}, status=403)
        try:
            cerrar_dia(dia=dia, fondo=request.POST.get('fondo'), contado=request.POST.get('contado'),
                       nota=request.POST.get('nota', ''), usuario=request.user)
        except VentaError as e:
            error = str(e)
        else:
            messages.success(request, f'Día {dia:%d/%m/%Y} cerrado')
            return redirect(f"{reverse('ventas:cierre')}?dia={dia.isoformat()}")

    r = resumen_dia(dia)
    guardado = CierreCaja.objects.filter(dia=dia).select_related('usuario').first()
    return render(request, 'ventas/cierre.html', {
        'r': r,
        'dia': dia,
        'hoy': timezone.localdate(),
        'guardado': guardado,
        'cambio_despues': bool(guardado and (guardado.total_vendido != r['total'] or guardado.ventas_efectivo != r['efectivo'])),
        'anteriores': CierreCaja.objects.select_related('usuario')[:10],
        'error': error,
        'fondo': request.POST.get('fondo', guardado.fondo if guardado else ''),
        'contado': request.POST.get('contado', guardado.contado if guardado else ''),
        'nota': request.POST.get('nota', guardado.nota if guardado else ''),
    }, status=400 if error else 200)


@xframe_options_sameorigin  # se imprime desde un marco escondido en la misma página
@requiere('ventas')
def cierre_imprimir(request):
    """Hoja del cierre para la impresora de 80 mm. Usa lo escrito en pantalla (aunque no se haya guardado)."""
    dia = _dia(request)
    r = resumen_dia(dia)
    guardado = CierreCaja.objects.filter(dia=dia).select_related('usuario').first()

    def numero(nombre, respaldo):
        try:
            return Decimal(request.GET.get(nombre, '').strip())
        except (InvalidOperation, ValueError):
            return respaldo

    fondo = numero('fondo', guardado.fondo if guardado else Decimal('0'))
    contado = numero('contado', guardado.contado if guardado else None)
    esperado = fondo + r['efectivo']
    diferencia = contado - esperado if contado is not None else None
    return render(request, 'ventas/cierre_imprimir.html', {
        'r': r, 'guardado': guardado, 'fondo': fondo, 'contado': contado, 'esperado': esperado,
        'diferencia': diferencia, 'imprimir': request.GET.get('imprimir') == '1',
    })
