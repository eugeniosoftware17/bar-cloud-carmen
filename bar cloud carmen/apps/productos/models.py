from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower


class Categoria(models.Model):
    nombre = models.CharField('nombre', max_length=40, unique=True)
    orden = models.PositiveSmallIntegerField('orden', default=0, help_text='Orden de las pestañas en Venta directa.')

    class Meta:
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class Dibujo(models.TextChoices):
        CERVEZA = 'cerveza', 'Botella de cerveza'
        RON = 'ron', 'Botella de licor'
        REFRESCO = 'refresco', 'Refresco'
        AGUA = 'agua', 'Agua'
        JUGO = 'jugo', 'Vaso de jugo'
        PINA = 'pina', 'Copa'
        MOJITO = 'mojito', 'Trago largo'
        BURGER = 'burger', 'Hamburguesa'
        POLLO = 'pollo', 'Pollo'
        TOSTONES = 'tostones', 'Plato'
        SANDWICH = 'sandwich', 'Sándwich'
        BOLSA = 'bolsa', 'Bolsa'
        HIELO = 'hielo', 'Hielo'
        VASO = 'vaso', 'Vaso'
        CAJA = 'caja', 'Caja'

    nombre = models.CharField('nombre', max_length=40)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos', verbose_name='categoría')
    precio = models.DecimalField('precio de venta', max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    costo = models.DecimalField('costo de compra', max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    controla_stock = models.BooleanField(
        'controlar inventario', default=True,
        help_text='Desmárcalo para productos que se preparan al momento (tragos, comida).',
    )
    stock = models.IntegerField('stock', default=0)
    stock_minimo = models.PositiveIntegerField('avisar cuando queden', default=0)
    dibujo = models.CharField('dibujo', max_length=12, choices=Dibujo.choices, default=Dibujo.CAJA)
    color = models.CharField(
        'color del dibujo', max_length=7, default='#b08a5a',
        validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Usa un color como #7a3b12.')],
        help_text='Solo cambia el color de las botellas de licor, bolsas y cajas.',
    )
    foto = models.ImageField('foto', upload_to='productos/', blank=True, help_text='Opcional. Si no hay foto se usa el dibujo.')
    activo = models.BooleanField('activo', default=True, help_text='Aparece para vender.')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'producto'
        verbose_name_plural = 'productos'
        ordering = ['categoria__orden', 'nombre']
        constraints = [
            models.UniqueConstraint(Lower('nombre'), name='producto_nombre_unico', violation_error_message='Ya existe un producto con ese nombre.'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def estado_stock(self):
        """'na' (no se controla), 'agotado', 'bajo' u 'ok'."""
        if not self.controla_stock:
            return 'na'
        if self.stock <= 0:
            return 'agotado'
        if self.stock <= self.stock_minimo:
            return 'bajo'
        return 'ok'

    @property
    def margen(self):
        if not self.precio:
            return 0
        return round((self.precio - self.costo) / self.precio * 100)
