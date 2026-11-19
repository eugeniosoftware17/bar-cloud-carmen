from django.db import models
from django.db.models.functions import Lower


class Proveedor(models.Model):
    nombre = models.CharField('nombre del proveedor', max_length=60)
    contacto = models.CharField('persona de contacto', max_length=60, blank=True)
    telefono = models.CharField('teléfono', max_length=30, blank=True)
    suple = models.CharField('qué te suple', max_length=120, blank=True)
    nota = models.CharField('nota', max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'proveedor'
        verbose_name_plural = 'proveedores'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(Lower('nombre'), name='proveedor_nombre_unico', violation_error_message='Ya existe un proveedor con ese nombre.'),
        ]

    def __str__(self):
        return self.nombre
