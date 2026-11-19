from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Gasto(models.Model):
    class Categoria(models.TextChoices):
        ALQUILER = 'Alquiler', 'Alquiler'
        SERVICIOS = 'Servicios', 'Servicios (luz, agua, internet)'
        SUELDOS = 'Sueldos', 'Sueldos'
        INSUMOS = 'Insumos', 'Insumos'
        MANTENIMIENTO = 'Mantenimiento', 'Mantenimiento'
        IMPUESTOS = 'Impuestos', 'Impuestos'
        OTROS = 'Otros', 'Otros'

    fecha = models.DateField('fecha', default=timezone.localdate, db_index=True)
    concepto = models.CharField('concepto', max_length=60)
    categoria = models.CharField('categoría', max_length=14, choices=Categoria.choices, default=Categoria.INSUMOS)
    monto = models.DecimalField('monto (RD$)', max_digits=12, decimal_places=2, validators=[MinValueValidator(1)])
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='gastos', verbose_name='registró')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'gasto'
        verbose_name_plural = 'gastos'
        ordering = ['-fecha', '-pk']

    def __str__(self):
        return f'{self.concepto} ({self.fecha:%d/%m/%Y})'
