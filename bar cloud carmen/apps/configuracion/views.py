from django.contrib import messages
from django.shortcuts import redirect, render

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
