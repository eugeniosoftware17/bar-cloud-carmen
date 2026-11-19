from django.db.models import F
from django.urls import reverse
from django.utils.safestring import mark_safe

from apps.configuracion.models import Configuracion
from apps.productos.models import Producto

from .menu import MENU
from .permisos import permisos_de


class _Puede(dict):
    """En plantillas: {{ PUEDE.mesas.ver }} / {{ PUEDE.mesas.editar }}."""

    def __missing__(self, clave):
        return {'ver': False, 'editar': False}


def barcloud(request):
    """Datos comunes a todas las páginas: configuración del negocio, permisos y menú lateral."""
    conf = Configuracion.obtener()
    datos = {'CONF': conf, 'NEGOCIO': conf.nombre}
    if not request.user.is_authenticated:
        return datos

    permisos = permisos_de(request.user)
    puede = _Puede({m: {'ver': True, 'editar': n == 'editar'} for m, n in permisos.items()})
    match = getattr(request, 'resolver_match', None)
    actual = match.namespace if match else ''
    insignias = {}
    if puede['inventario']['ver']:
        bajos = Producto.objects.filter(activo=True, controla_stock=True, stock__lte=F('stock_minimo')).count()
        if bajos:
            insignias['inventario'] = bajos
    menu = [
        {
            'href': reverse(item['url']),
            'texto': item['texto'],
            'icono': mark_safe(item['icono']),
            'activo': item['clave'] == actual,
            'insignia': insignias.get(item['clave']),
        }
        for item in MENU
        if puede[item['clave']]['ver']
    ]
    titulo = next((m['texto'] for m in menu if m['activo']), 'Bar Cloud')
    datos.update({
        'PUEDE': puede,
        'ES_DUENO': request.user.is_superuser,
        'MENU': menu,
        'TITULO_MODULO': titulo,
    })
    return datos
