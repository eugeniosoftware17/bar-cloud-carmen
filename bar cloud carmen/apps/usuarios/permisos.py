"""Permisos por usuario y por módulo.

- El dueño del sistema (superusuario) tiene todo.
- A los demás, el administrador les marca cada módulo: sin acceso, "Solo ver" o "Ver y editar".
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import CLAVES, Permiso

NIVELES = {None: 0, 'ver': 1, 'editar': 2}


def permisos_de(user):
    """{modulo: 'ver' | 'editar'} del usuario (se guarda en el objeto para no repetir consultas)."""
    if not user.is_authenticated or not user.is_active:
        return {}
    if user.is_superuser:
        return {c: 'editar' for c in CLAVES}
    if not hasattr(user, '_permisos_bc'):
        user._permisos_bc = dict(Permiso.objects.filter(usuario=user).values_list('modulo', 'nivel'))
    return user._permisos_bc


def puede(user, modulo, nivel='ver'):
    return NIVELES[permisos_de(user).get(modulo)] >= NIVELES[nivel]


def es_dueno(user):
    return user.is_authenticated and user.is_superuser


def primera_pantalla(user):
    """URL del primer módulo que el usuario puede ver (para llevarlo ahí al entrar)."""
    from .menu import MENU
    for item in MENU:
        if puede(user, item['clave']):
            return reverse(item['url'])
    return None


def _quiere_json(request):
    return request.content_type == 'application/json' or request.headers.get('Accept', '').startswith('application/json')


def requiere(modulo, nivel='ver'):
    """Exige sesión y permiso en el módulo. Sin permiso: aviso de bloqueo (o JSON si es una acción de la pantalla)."""
    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not puede(request.user, modulo, nivel):
                if _quiere_json(request):
                    texto = 'No tienes permiso para hacer esto.' if puede(request.user, modulo) else 'No tienes acceso a este módulo.'
                    return JsonResponse({'ok': False, 'error': texto}, status=403)
                return render(request, 'bloqueo.html', {
                    'solo_ver': puede(request.user, modulo),
                    'inicio': primera_pantalla(request.user),
                }, status=403)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def requiere_alguno(*modulos):
    """Exige poder ver al menos uno de los módulos (p. ej. el recibo: Venta directa, Mesas o Ventas)."""
    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not any(puede(request.user, m) for m in modulos):
                return render(request, 'bloqueo.html', {'inicio': primera_pantalla(request.user)}, status=403)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def guardar_permisos(user, permisos):
    """permisos: {modulo: 'ver' | 'editar' | ''}. Reemplaza los del usuario."""
    Permiso.objects.filter(usuario=user).delete()
    Permiso.objects.bulk_create([
        Permiso(usuario=user, modulo=m, nivel=n) for m, n in permisos.items() if m in CLAVES and n in ('ver', 'editar')
    ])
    if hasattr(user, '_permisos_bc'):
        del user._permisos_bc


def ir_a_inicio(user):
    url = primera_pantalla(user)
    return redirect(url) if url else None


# Plantilla de permisos de un cajero típico (la usa el atajo "Caja" y las pruebas).
PLANTILLA_CAJA = {'venta_directa': 'editar', 'mesas': 'editar', 'productos': 'ver'}
