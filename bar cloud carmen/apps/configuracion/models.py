from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

PORCENTAJE = [MinValueValidator(0), MaxValueValidator(100)]


class Configuracion(models.Model):
    """Datos del negocio, cargos y textos del recibo. Hay un solo registro (pk=1) y lo cambia el administrador."""

    # negocio
    nombre = models.CharField('nombre del negocio', max_length=60, default='Mi negocio')
    direccion = models.CharField('dirección', max_length=120, blank=True)
    telefono = models.CharField('teléfono', max_length=30, blank=True)

    # cargos
    cobrar_propina = models.BooleanField('cobrar propina legal', default=True)
    propina_porcentaje = models.DecimalField('propina (%)', max_digits=5, decimal_places=2, default=10, validators=PORCENTAJE)
    cobrar_itbis = models.BooleanField('cobrar ITBIS', default=True)
    itbis_porcentaje = models.DecimalField('ITBIS (%)', max_digits=5, decimal_places=2, default=18, validators=PORCENTAJE)

    # recibo
    class Diseno(models.TextChoices):
        CLASICO = 'clasico', 'Clásico (letra de máquina, líneas punteadas)'
        MODERNO = 'moderno', 'Moderno (letra limpia, total resaltado en negro)'
        DETALLADO = 'detallado', 'Detallado (precio de cada producto, total grande)'

    class Letra(models.TextChoices):
        NORMAL = 'normal', 'Normal'
        GRANDE = 'grande', 'Grande'
        MUY_GRANDE = 'muy_grande', 'Muy grande'

    class Ancho(models.TextChoices):
        AUTO = 'auto', 'Automático (el de la impresora)'
        MM80 = '80', 'Papel de 80 mm'
        MM58 = '58', 'Papel de 58 mm'

    recibo_diseno = models.CharField('diseño del recibo', max_length=10, choices=Diseno.choices, default=Diseno.CLASICO)
    recibo_letra = models.CharField('tamaño de letra', max_length=10, choices=Letra.choices, default=Letra.GRANDE)
    recibo_ancho = models.CharField('ancho del papel', max_length=4, choices=Ancho.choices, default=Ancho.AUTO,
                                    help_text='Si el recibo sale cortado a la derecha, prueba con 58 mm.')
    recibo_imprimir_al_cobrar = models.BooleanField(
        'imprimir al cobrar', default=True,
        help_text='El recibo se manda a la impresora apenas se cobra, sin tocar ningún botón.')
    recibo_dos_copias = models.BooleanField('imprimir dos copias', default=True,
                                            help_text='Una para el cliente y otra para el negocio.')
    recibo_copias_separadas = models.BooleanField(
        'copias por separado', default=True,
        help_text='Cada copia se manda como una impresión aparte, así la impresora corta entre una y otra.')
    recibo_mostrar_atendio = models.BooleanField('mostrar quién atendió', default=True)
    recibo_mensaje = models.CharField('mensaje de despedida', max_length=80, blank=True, default='¡Gracias por su visita!')
    recibo_mostrar_aviso = models.BooleanField('mostrar aviso al pie', default=True)
    recibo_aviso = models.CharField('texto del aviso', max_length=80, blank=True, default='Recibo interno · sin valor fiscal')

    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuración'
        verbose_name_plural = 'configuración'

    def __str__(self):
        return 'Configuración del negocio'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        conf = cls.objects.filter(pk=1).first()
        if conf is None:
            conf = cls(nombre=getattr(settings, 'NEGOCIO_NOMBRE', 'Mi negocio'),
                       direccion=getattr(settings, 'NEGOCIO_DIRECCION', ''))
            conf.save()
        return conf

    @property
    def tasa_propina(self):
        """Fracción que se cobra (0 si está desactivada)."""
        return self.propina_porcentaje / Decimal(100) if self.cobrar_propina else Decimal(0)

    @property
    def recibo_estilo(self):
        """Medidas del recibo para la plantilla: letra en px y ancho en pantalla / al imprimir."""
        letra = {'normal': 12, 'grande': 14, 'muy_grande': 16}.get(self.recibo_letra, 14)
        imprimir = {'80': '72mm', '58': '48mm'}.get(self.recibo_ancho, '100%')
        return {
            'letra': letra,
            'pantalla': {'58': '48mm'}.get(self.recibo_ancho, '72mm'),
            'imprimir': imprimir,
            'relleno': '0 2mm' if imprimir == '100%' else '0',
            'diseno': self.recibo_diseno if self.recibo_diseno in self.Diseno.values else self.Diseno.CLASICO,
        }

    @property
    def tasa_itbis(self):
        return self.itbis_porcentaje / Decimal(100) if self.cobrar_itbis else Decimal(0)
