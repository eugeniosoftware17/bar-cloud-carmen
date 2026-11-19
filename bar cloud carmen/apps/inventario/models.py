from django.conf import settings
from django.db import models


class Movimiento(models.Model):
    """Cada cambio de stock de un producto: entradas, ventas, anulaciones y ajustes."""

    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        VENTA = 'venta', 'Venta'
        ANULACION = 'anulacion', 'Anulación'
        AJUSTE = 'ajuste', 'Ajuste'

    fecha = models.DateTimeField('fecha', auto_now_add=True, db_index=True)
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField('tipo', max_length=10, choices=Tipo.choices)
    cantidad = models.IntegerField('cantidad', help_text='Positiva si entra, negativa si sale.')
    stock_despues = models.IntegerField('stock después')
    costo = models.DecimalField('costo por unidad', max_digits=10, decimal_places=2, default=0)
    nota = models.CharField('nota', max_length=200, blank=True)
    proveedor = models.ForeignKey('proveedores.Proveedor', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='movimientos', verbose_name='proveedor')
    venta = models.ForeignKey('ventas.Venta', on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimientos')

    class Meta:
        verbose_name = 'movimiento de inventario'
        verbose_name_plural = 'movimientos de inventario'
        ordering = ['-fecha', '-pk']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad:+d} {self.producto}'
