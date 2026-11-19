"""Pasa los roles anteriores a permisos por módulo:
- grupo "Administrador" → todos los módulos con "Ver y editar"
- cualquier otro usuario (Caja) → Venta directa y Mesas para editar, Productos solo ver.
"""
from django.db import migrations

TODOS = ['venta_directa', 'mesas', 'productos', 'inventario', 'ventas', 'proveedores', 'reportes', 'usuarios', 'configuracion']
CAJA = {'venta_directa': 'editar', 'mesas': 'editar', 'productos': 'ver'}


def pasar(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permiso = apps.get_model('usuarios', 'Permiso')
    for u in User.objects.filter(is_superuser=False):
        if u.groups.filter(name='Administrador').exists():
            permisos = {m: 'editar' for m in TODOS}
        else:
            permisos = CAJA
        Permiso.objects.bulk_create([Permiso(usuario=u, modulo=m, nivel=n) for m, n in permisos.items()])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(pasar, migrations.RunPython.noop),
    ]
