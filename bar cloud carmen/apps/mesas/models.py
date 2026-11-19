from decimal import Decimal

from django.conf import settings
from django.db import models


class Mesa(models.Model):
    nombre = models.CharField('nombre', max_length=30, unique=True)
    orden = models.PositiveSmallIntegerField('orden', default=0)
    activa = models.BooleanField('activa', default=True, help_text='Las mesas desactivadas no aparecen en la pantalla.')
    # cuenta abierta (vacío = mesa libre)
    abierta_en = models.DateTimeField('cuenta abierta en', null=True, blank=True)
    abierta_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='mesas_abiertas', verbose_name='abrió la cuenta')

    class Meta:
        verbose_name = 'mesa'
        verbose_name_plural = 'mesas'
        ordering = ['orden', 'pk']

    def __str__(self):
        return self.nombre

    @property
    def ocupada(self):
        return self.abierta_en is not None

    def lineas(self):
        """Consumos con su importe, para pintar la cuenta."""
        return [c for c in self.consumos.select_related('producto').order_by('pk')]

    def subtotal(self):
        return sum((c.importe for c in self.consumos.select_related('producto')), Decimal('0'))


class Consumo(models.Model):
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, related_name='consumos')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='consumos_mesa')
    cantidad = models.PositiveIntegerField('cantidad')
    agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'consumo'
        verbose_name_plural = 'consumos'
        constraints = [models.UniqueConstraint(fields=['mesa', 'producto'], name='consumo_unico_por_mesa')]

    def __str__(self):
        return f'{self.cantidad} x {self.producto} ({self.mesa})'

    @property
    def importe(self):
        return self.producto.precio * self.cantidad
