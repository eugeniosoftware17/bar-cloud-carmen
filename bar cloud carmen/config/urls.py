from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.usuarios.views import Entrar, Salir

urlpatterns = [
    path('entrar/', Entrar.as_view(), name='login'),
    path('salir/', Salir.as_view(), name='logout'),

    path('', include('apps.venta_directa.urls')),
    path('mesas/', include('apps.mesas.urls')),
    path('productos/', include('apps.productos.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('ventas/', include('apps.ventas.urls')),
    path('proveedores/', include('apps.proveedores.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('configuracion/', include('apps.configuracion.urls')),

    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
