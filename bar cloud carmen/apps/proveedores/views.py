from django.contrib import messages
from django.db.models import DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.permisos import requiere

from .forms import ProveedorForm
from .models import Proveedor


def _lista(q):
    entradas = Q(movimientos__tipo='entrada')
    lista = Proveedor.objects.annotate(
        compras=Coalesce(Sum(ExpressionWrapper(F('movimientos__cantidad') * F('movimientos__costo'), output_field=DecimalField()),
                             filter=entradas), 0, output_field=DecimalField()),
        ultima=Max('movimientos__fecha', filter=entradas),
    )
    if q:
        lista = lista.filter(Q(nombre__icontains=q) | Q(contacto__icontains=q) | Q(suple__icontains=q) | Q(telefono__icontains=q))
    return lista


def _pagina(request, form=None, proveedor=None, modo='', status=200):
    q = request.GET.get('q', '').strip()
    ultimas = proveedor.movimientos.filter(tipo='entrada').select_related('producto')[:8] if proveedor else []
    return render(request, 'proveedores/inicio.html', {
        'proveedores': _lista(q), 'q': q, 'form': form, 'proveedor': proveedor, 'modo': modo, 'ultimas': ultimas,
    }, status=status)


@requiere('proveedores')
def inicio(request):
    return _pagina(request)


@requiere('proveedores', 'editar')
def nuevo(request):
    form = ProveedorForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor creado')
            return redirect('proveedores:inicio')
        return _pagina(request, form=form, modo='nuevo', status=400)
    return _pagina(request, form=form, modo='nuevo')


@requiere('proveedores', 'editar')
def editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Cambios guardados')
            return redirect('proveedores:inicio')
        return _pagina(request, form=form, proveedor=proveedor, modo='editar', status=400)
    return _pagina(request, form=form, proveedor=proveedor, modo='editar')


@requiere('proveedores', 'editar')
def eliminar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        nombre = proveedor.nombre
        proveedor.delete()  # sus entradas de inventario se conservan, sin proveedor
        messages.success(request, f'Proveedor {nombre} eliminado')
        return redirect('proveedores:inicio')
    return _pagina(request, proveedor=proveedor, modo='eliminar')
