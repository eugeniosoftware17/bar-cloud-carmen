from decimal import Decimal
from types import SimpleNamespace

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
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


ACCESO_CAJA = r'''@echo off
rem Bar Cloud - Caja
rem Abre el sistema con impresion directa: recibos y pre-cuentas salen de inmediato
rem por la impresora PREDETERMINADA de Windows, sin la ventana de imprimir.
rem Usa un perfil aparte del navegador para que la impresion directa siempre funcione.

set "URL={url}"
set "PERFIL=%LOCALAPPDATA%\BarCloudCaja"
set "NAV="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "NAV=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "NAV=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "NAV=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "NAV=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined NAV if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "NAV=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined NAV goto sinnavegador

start "" "%NAV%" --kiosk-printing --user-data-dir="%PERFIL%" --no-first-run --no-default-browser-check --start-maximized --app="%URL%"
exit /b 0

:sinnavegador
echo No se encontro Google Chrome ni Microsoft Edge en este equipo.
echo Instala Google Chrome y vuelve a abrir este archivo.
pause
exit /b 1
'''


@requiere('configuracion')
def acceso_caja(request):
    """Descarga "Bar Cloud - Caja.bat": abre el sistema con impresión directa en la impresora predeterminada."""
    url = request.build_absolute_uri(reverse('venta_directa:inicio'))
    contenido = ACCESO_CAJA.replace('{url}', url).replace('\r\n', '\n').replace('\n', '\r\n')
    resp = HttpResponse(contenido.encode('ascii', 'ignore'), content_type='application/octet-stream')
    resp['Content-Disposition'] = 'attachment; filename="Bar Cloud - Caja.bat"'
    return resp


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
