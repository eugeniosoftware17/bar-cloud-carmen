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
    recibo_dos_copias = models.BooleanField('imprimir dos copias', default=True,
                                            help_text='Una para el cliente y otra para el negocio, en la misma impresión.')
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
    def tasa_itbis(self):
        return self.itbis_porcentaje / Decimal(100) if self.cobrar_itbis else Decimal(0)
