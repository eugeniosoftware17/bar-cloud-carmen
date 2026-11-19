from django.conf import settings
from django.db import models

# Módulos que el administrador puede dar a cada usuario (clave, nombre, qué permite "editar").
MODULOS = [
    ('venta_directa', 'Venta directa', 'Cobrar ventas'),
    ('mesas', 'Mesas', 'Abrir cuentas, agregar consumos, cobrar, liberar y agregar mesas'),
    ('productos', 'Productos', 'Crear y editar productos; ver costos y margen'),
    ('inventario', 'Inventario', 'Registrar entradas y ajustes'),
    ('ventas', 'Ventas', 'Anular ventas y cerrar el día'),
    ('proveedores', 'Proveedores', 'Crear y editar proveedores'),
    ('reportes', 'Reportes', 'Registrar, editar y eliminar gastos'),
    ('usuarios', 'Usuarios', 'Crear usuarios, cambiar permisos y contraseñas'),
    ('configuracion', 'Configuración', 'Cambiar datos del negocio, cargos y recibo'),
]
CLAVES = [m[0] for m in MODULOS]


class Permiso(models.Model):
    class Nivel(models.TextChoices):
        VER = 'ver', 'Solo ver'
        EDITAR = 'editar', 'Ver y editar'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='permisos_modulo')
    modulo = models.CharField('módulo', max_length=20, choices=[(c, n) for c, n, _ in MODULOS])
    nivel = models.CharField('nivel', max_length=6, choices=Nivel.choices)

    class Meta:
        verbose_name = 'permiso'
        verbose_name_plural = 'permisos'
        constraints = [models.UniqueConstraint(fields=['usuario', 'modulo'], name='permiso_unico_por_modulo')]

    def __str__(self):
        return f'{self.usuario} · {self.get_modulo_display()} · {self.get_nivel_display()}'
