from django.contrib import messages
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.usuarios.permisos import puede, requiere

from .forms import ProductoForm
from .models import Categoria, Producto

ESTADOS = [('', 'Todos'), ('activo', 'Activos'), ('inactivo', 'Desactivados'), ('bajo', 'Poco stock o agotados')]


def _filtrar(request):
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', '')
    estado = request.GET.get('estado', '')
    lista = Producto.objects.select_related('categoria').prefetch_related('componentes__producto')
    if q:
        lista = lista.filter(nombre__icontains=q)
    if cat.isdigit():
        lista = lista.filter(categoria_id=cat)
    if estado == 'activo':
        lista = lista.filter(activo=True)
    elif estado == 'inactivo':
        lista = lista.filter(activo=False)
    elif estado == 'bajo':
        lista = lista.filter(controla_stock=True).filter(Q(stock__lte=0) | Q(stock__lte=F('stock_minimo')))
    filtros = {'q': q, 'cat': cat, 'estado': estado}
    return lista, filtros


def _pagina(request, form=None, producto=None, status=200):
    lista, filtros = _filtrar(request)
    return render(request, 'productos/inicio.html', {
        'productos': lista,
        'categorias': Categoria.objects.all(),
        'estados': ESTADOS,
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'hay_productos': Producto.objects.exists(),
        'form': form,
        'costos': {p.pk: float(p.costo) for p in Producto.objects.filter(es_combo=False)} if form else {},
        'producto': producto,
        'volver': _destino(request),
        'admin': puede(request.user, 'productos', 'editar'),
    }, status=status)


def _destino(request):
    """Filtros de la lista a los que se vuelve (solo se acepta una query string, nunca otra dirección)."""
    destino = request.POST.get('volver') or request.GET.get('volver') or ''
    return destino if destino.startswith('?') else ''


def _volver(request):
    return redirect(reverse('productos:inicio') + _destino(request))


@requiere('productos')
def inicio(request):
    return _pagina(request)


@requiere('productos', 'editar')
def nuevo(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                form.save(usuario=request.user)
            messages.success(request, 'Producto creado')
            return _volver(request)
        return _pagina(request, form=form, status=400)
    return _pagina(request, form=ProductoForm())


@requiere('productos', 'editar')
def editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cambios guardados')
            return _volver(request)
        return _pagina(request, form=form, producto=producto, status=400)
    return _pagina(request, form=ProductoForm(instance=producto), producto=producto)
