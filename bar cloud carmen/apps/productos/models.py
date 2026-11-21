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
    es_combo = models.BooleanField(
        'es combo', default=False,
        help_text='Se arma con otros productos: al venderlo se descuentan del inventario los productos que lo forman.',
    )
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
    def disponibles(self):
        """Unidades que se pueden vender. None = sin límite (no se controla el inventario).

        Un combo no tiene stock propio: alcanza para tantos como permita el producto que se acabe primero.
        """
        if not self.es_combo:
            return self.stock if self.controla_stock else None
        limites = [max(c.producto.stock, 0) // c.cantidad
                   for c in self.componentes.all() if c.producto.controla_stock]
        if limites:
            return min(limites)
        return None if self.componentes.all() else 0  # combo sin productos: no se puede vender

    @property
    def stock_js(self):
        """Para las tarjetas de venta: -1 significa sin límite."""
        d = self.disponibles
        return -1 if d is None else d

    @property
    def estado_stock(self):
        """'na' (no se controla), 'agotado', 'bajo' u 'ok'."""
        d = self.disponibles
        if d is None:
            return 'na'
        if d <= 0:
            return 'agotado'
        if self.es_combo:
            return 'ok'
        if d <= self.stock_minimo:
            return 'bajo'
        return 'ok'

    def costo_combo(self):
        """Suma del costo de los productos que forman el combo (con sus costos de hoy)."""
        return sum((c.producto.costo * c.cantidad for c in self.componentes.all()), 0)

    @property
    def margen(self):
        if not self.precio:
            return 0
        return round((self.precio - self.costo) / self.precio * 100)


class ComboItem(models.Model):
    """Un producto que forma parte de un combo y cuántas unidades lleva."""
    combo = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='componentes', verbose_name='combo')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='en_combos', verbose_name='producto')
    cantidad = models.PositiveIntegerField('cantidad', default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'producto del combo'
        verbose_name_plural = 'productos del combo'
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(fields=['combo', 'producto'], name='combo_producto_unico'),
        ]

    def __str__(self):
        return f'{self.cantidad} × {self.producto} en {self.combo}'


def descomponer(pares):
    """[(producto_id, cantidad), …] → {producto_id: unidades} cambiando cada combo por los productos que lo forman.

    Un combo sin productos queda tal cual (quien llama decide si eso es un error).
    """
    pares = [(int(pid), int(cant)) for pid, cant in pares]
    recetas = {}
    for combo_id, producto_id, cantidad in ComboItem.objects.filter(
            combo_id__in={pid for pid, _ in pares}, combo__es_combo=True).values_list('combo_id', 'producto_id', 'cantidad'):
        recetas.setdefault(combo_id, []).append((producto_id, cantidad))
    total = {}
    for pid, cant in pares:
        for base, por_unidad in recetas.get(pid, [(pid, 1)]):
            total[base] = total.get(base, 0) + por_unidad * cant
    return total


def actualizar_costo_combos(producto):
    """Cuando cambia el costo de un producto, los combos que lo llevan recalculan el suyo."""
    for combo in Producto.objects.filter(es_combo=True, componentes__producto=producto).distinct().prefetch_related('componentes__producto'):
        nuevo = combo.costo_combo()
        if nuevo != combo.costo:
            combo.costo = nuevo
            combo.save(update_fields=['costo', 'actualizado'])
