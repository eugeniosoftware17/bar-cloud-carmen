from decimal import Decimal
from types import SimpleNamespace

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.usuarios.permisos import puede, requiere

from .forms import ConfiguracionForm
from .models import Configuracion


@requiere('configuracion')
def inicio(request):
    conf = Configuracion.obtener()
    form = ConfiguracionForm(request.POST or None, instance=conf)
    if not puede(request.user, 'configuracion', 'editar'):
        for campo in form.fields.values():
            campo.disabled = True
    if request.method == 'POST':
        if not puede(request.user, 'configuracion', 'editar'):
            return render(request, 'bloqueo.html', {'solo_ver': True}, status=403)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración guardada')
            return redirect('configuracion:inicio')
        status = 400
    else:
        status = 200
    return render(request, 'configuracion/inicio.html', {'form': form, 'conf': conf}, status=status)


@xframe_options_sameorigin  # se muestra dentro de la página de Configuración
@requiere('configuracion')
def muestra_recibo(request):
    """Recibo de ejemplo con lo que está escrito en el formulario (sin guardarlo)."""
    conf = Configuracion.obtener()
    if request.GET:
        form = ConfiguracionForm(request.GET, instance=conf)
        form.is_valid()  # pasa los valores al objeto; nunca se guarda aquí
        conf = form.instance
    dos = conf.recibo_dos_copias
    sub = Decimal('300')
    propina = (sub * conf.tasa_propina).quantize(Decimal('1'))
    itbis = (sub * conf.tasa_itbis).quantize(Decimal('1'))
    lineas = [
        SimpleNamespace(cantidad=1, nombre='Cerveza Presidente', precio=Decimal('150'), importe=Decimal('150')),
        SimpleNamespace(cantidad=2, nombre='Agua', precio=Decimal('75'), importe=Decimal('150')),
    ]
    venta = SimpleNamespace(
        numero='0001', origen='Directa', fecha=timezone.now(), atendio=request.user.get_username(), anulada=False,
        lineas=SimpleNamespace(all=lambda: lineas), subtotal=sub, propina=propina, itbis=itbis,
        total=sub + propina + itbis, metodo='Efectivo', recibido=Decimal('500'), cambio=Decimal('500') - (sub + propina + itbis),
        referencia='',
    )
    return render(request, 'ventas/recibo.html', {
        'CONF': conf, 'venta': venta, 'muestra': True, 'dos_copias': dos,
        'copias': ['COPIA CLIENTE', 'COPIA NEGOCIO'] if dos else [''],
    })
