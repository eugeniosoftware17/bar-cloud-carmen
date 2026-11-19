from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.permisos import requiere

from . import calculos
from .forms import GastoForm
from .models import Gasto


@requiere('reportes')
def inicio(request):
    rango = request.GET.get('rango', '7')
    gran = request.GET.get('gran', 'dia')
    if rango not in dict(calculos.RANGOS):
        rango = '7'
    if gran not in dict(calculos.GRANOS):
        gran = 'dia'
    return render(request, 'reportes/estadisticas.html', {
        'seccion': 'estadisticas', 'e': calculos.estadisticas(rango, gran),
        'rango': rango, 'gran': gran, 'rangos': calculos.RANGOS, 'granos': calculos.GRANOS,
    })


def _mes(request):
    texto = request.GET.get('mes') or request.POST.get('mes') or ''
    hoy = timezone.localdate()
    try:
        anio, mes = (int(x) for x in texto.split('-'))
        if not 1 <= mes <= 12 or anio < 2000:
            raise ValueError
    except ValueError:
        anio, mes = hoy.year, hoy.month
    return anio, mes


def _ganancias(request, form=None, gasto=None, modo='', status=200):
    anio, mes = _mes(request)
    return render(request, 'reportes/ganancias.html', {
        'seccion': 'ganancias', 'g': calculos.ganancias(anio, mes), 'mes': f'{anio}-{mes:02d}',
        'mes_texto': f'{calculos.MESES[mes - 1]} {anio}', 'form': form, 'gasto': gasto, 'modo': modo,
    }, status=status)


def _volver_al_mes(fecha):
    return redirect(f"{reverse('reportes:ganancias')}?mes={fecha:%Y-%m}")


@requiere('reportes')
def ganancias(request):
    return _ganancias(request)


@requiere('reportes', 'editar')
def gasto_nuevo(request):
    form = GastoForm(request.POST or None, initial={'fecha': timezone.localdate()})
    if request.method == 'POST':
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.usuario = request.user
            gasto.save()
            messages.success(request, 'Gasto registrado')
            return _volver_al_mes(gasto.fecha)
        return _ganancias(request, form=form, modo='nuevo', status=400)
    return _ganancias(request, form=form, modo='nuevo')


@requiere('reportes', 'editar')
def gasto_editar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    form = GastoForm(request.POST or None, instance=gasto)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto guardado')
            return _volver_al_mes(gasto.fecha)
        return _ganancias(request, form=form, gasto=gasto, modo='editar', status=400)
    return _ganancias(request, form=form, gasto=gasto, modo='editar')


@requiere('reportes', 'editar')
def gasto_eliminar(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk)
    if request.method == 'POST':
        fecha = gasto.fecha
        gasto.delete()
        messages.success(request, 'Gasto eliminado')
        return _volver_al_mes(fecha)
    return _ganancias(request, gasto=gasto, modo='eliminar')
