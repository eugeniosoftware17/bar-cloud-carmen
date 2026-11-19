from django.shortcuts import render

from apps.productos.models import Categoria, Producto
from apps.usuarios.permisos import requiere


@requiere('venta_directa')
def inicio(request):
    categorias = list(Categoria.objects.all())
    productos = Producto.objects.filter(activo=True).select_related('categoria')
    return render(request, 'venta_directa/inicio.html', {
        'categorias': categorias,
        'productos': productos,
        'categoria_inicial': categorias[0].pk if categorias else None,
    })
