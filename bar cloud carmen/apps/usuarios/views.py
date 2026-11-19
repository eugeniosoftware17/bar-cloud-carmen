from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ClaveForm, LoginForm, UsuarioForm
from .models import MODULOS
from .permisos import permisos_de, primera_pantalla, requiere


class Entrar(auth_views.LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # al entrar, ir al primer módulo que el usuario tiene permitido
        return primera_pantalla(self.request.user) or super().get_default_redirect_url()


class Salir(auth_views.LogoutView):
    pass


def _pagina(request, form=None, usuario=None, modo='', status=200):
    usuarios = list(User.objects.order_by('-is_active', 'username'))
    nombres = {c: n for c, n, _ in MODULOS}
    for u in usuarios:
        p = permisos_de(u)
        u.resumen = 'Todo (dueño)' if u.is_superuser else (
            ', '.join(f'{nombres[c]}{"" if n == "editar" else " (ver)"}' for c, n in p.items()) or 'Sin acceso')
    return render(request, 'usuarios/inicio.html', {
        'usuarios': usuarios, 'form': form, 'usuario': usuario, 'modo': modo,
    }, status=status)


def _sin_permiso_sobre(request, usuario):
    """Solo el dueño puede tocar la cuenta del dueño."""
    return usuario.is_superuser and not request.user.is_superuser


@requiere('usuarios')
def inicio(request):
    return _pagina(request)


@requiere('usuarios', 'editar')
def nuevo(request):
    form = UsuarioForm(request.POST or None, actual=request.user)
    if request.method == 'POST':
        if form.is_valid():
            u = form.save()
            messages.success(request, f'Usuario {u.username} creado')
            return redirect('usuarios:inicio')
        return _pagina(request, form=form, modo='nuevo', status=400)
    return _pagina(request, form=form, modo='nuevo')


@requiere('usuarios', 'editar')
def editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if _sin_permiso_sobre(request, usuario):
        messages.error(request, 'Solo el dueño del sistema puede cambiar su propia cuenta.')
        return redirect('usuarios:inicio')
    form = UsuarioForm(request.POST or None, instance=usuario, actual=request.user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Cambios guardados')
            return redirect('usuarios:inicio')
        return _pagina(request, form=form, usuario=usuario, modo='editar', status=400)
    return _pagina(request, form=form, usuario=usuario, modo='editar')


@requiere('usuarios', 'editar')
def clave(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if _sin_permiso_sobre(request, usuario):
        messages.error(request, 'Solo el dueño del sistema puede cambiar su propia contraseña.')
        return redirect('usuarios:inicio')
    form = ClaveForm(usuario, request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            if usuario.pk == request.user.pk:
                update_session_auth_hash(request, usuario)
            messages.success(request, f'Contraseña de {usuario.username} cambiada')
            return redirect('usuarios:inicio')
        return _pagina(request, form=form, usuario=usuario, modo='clave', status=400)
    return _pagina(request, form=form, usuario=usuario, modo='clave')
