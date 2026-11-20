from django.conf import settings
from django.db import models


class Venta(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = 'Efectivo', 'Efectivo'
        TARJETA = 'Tarjeta', 'Tarjeta'
        TRANSFERENCIA = 'Transferencia', 'Transferencia'

    fecha = models.DateTimeField('fecha', auto_now_add=True, db_index=True)
    mesa = models.CharField('mesa', max_length=40, blank=True, help_text='Vacío = venta directa en el mostrador.')
    metodo = models.CharField('método de pago', max_length=14, choices=Metodo.choices)
    subtotal = models.DecimalField('subtotal', max_digits=12, decimal_places=2)
    propina = models.DecimalField('propina legal', max_digits=12, decimal_places=2)
    itbis = models.DecimalField('ITBIS', max_digits=12, decimal_places=2)
    total = models.DecimalField('total', max_digits=12, decimal_places=2)
    recibido = models.DecimalField('recibido', max_digits=12, decimal_places=2)
    cambio = models.DecimalField('cambio', max_digits=12, decimal_places=2, default=0)
    referencia = models.CharField('referencia', max_length=60, blank=True)
    mesera = models.CharField('la atendió', max_length=40, blank=True, help_text='Quién atendió la mesa (vacío en venta directa).')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas', verbose_name='atendió')

    anulada = models.BooleanField('anulada', default=False)
    motivo_anulacion = models.CharField('motivo de anulación', max_length=200, blank=True)
    anulada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='ventas_anuladas', verbose_name='anulada por')
    anulada_en = models.DateTimeField('anulada en', null=True, blank=True)

    class Meta:
        verbose_name = 'venta'
        verbose_name_plural = 'ventas'
        ordering = ['-fecha', '-pk']

    def __str__(self):
        return f'Venta #{self.numero}'

    @property
    def numero(self):
        return f'{self.pk:04d}' if self.pk else ''

    @property
    def atendio(self):
        """Mesera de la mesa; si no hay, el usuario que cobró."""
        return self.mesera or self.usuario.get_full_name() or self.usuario.get_username()

    @property
    def origen(self):
        return self.mesa or 'Directa'


class CierreCaja(models.Model):
    """Cuadre de caja de un día: lo que debería haber en efectivo contra lo que se contó."""

    dia = models.DateField('día', unique=True)
    fondo = models.DecimalField('fondo inicial', max_digits=12, decimal_places=2, default=0)
    ventas_efectivo = models.DecimalField('ventas en efectivo', max_digits=12, decimal_places=2, default=0)
    total_vendido = models.DecimalField('total vendido', max_digits=12, decimal_places=2, default=0)
    num_ventas = models.PositiveIntegerField('ventas', default=0)
    esperado = models.DecimalField('efectivo esperado', max_digits=12, decimal_places=2)
    contado = models.DecimalField('efectivo contado', max_digits=12, decimal_places=2)
    diferencia = models.DecimalField('diferencia', max_digits=12, decimal_places=2)
    nota = models.CharField('nota', max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cierres', verbose_name='cerró')
    hora = models.DateTimeField('hora del cierre', auto_now=True)

    class Meta:
        verbose_name = 'cierre de caja'
        verbose_name_plural = 'cierres de caja'
        ordering = ['-dia']

    def __str__(self):
        return f'Cierre {self.dia:%d/%m/%Y}'

    @property
    def resultado(self):
        if self.diferencia == 0:
            return 'Cuadra'
        return 'Sobra' if self.diferencia > 0 else 'Falta'


class LineaVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='lineas_venta')
    nombre = models.CharField('producto', max_length=40, help_text='Nombre al momento de vender.')
    cantidad = models.PositiveIntegerField('cantidad')
    precio = models.DecimalField('precio', max_digits=10, decimal_places=2)
    costo = models.DecimalField('costo', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'línea de venta'
        verbose_name_plural = 'líneas de venta'
        ordering = ['pk']

    def __str__(self):
        return f'{self.cantidad} x {self.nombre}'

    @property
    def importe(self):
        return self.precio * self.cantidad
