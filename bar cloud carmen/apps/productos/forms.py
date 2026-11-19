from django import forms

from .models import Producto


class ProductoForm(forms.ModelForm):
    stock_inicial = forms.IntegerField(label='Stock inicial', min_value=0, initial=0, required=False)

    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'dibujo', 'color', 'precio', 'costo', 'stock_minimo',
                  'controla_stock', 'activo', 'foto']
        widgets = {
            'nombre': forms.TextInput(attrs={'maxlength': 40, 'placeholder': 'Ej.: Cerveza Presidente', 'autofocus': True}),
            'precio': forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'}),
            'costo': forms.NumberInput(attrs={'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'stock_minimo': forms.NumberInput(attrs={'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'color': forms.TextInput(attrs={'type': 'color'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        error_messages = {
            'nombre': {'required': 'Escribe el nombre del producto.'},
            'precio': {'required': 'Escribe el precio de venta.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = None
        self.fields['costo'].required = False
        if self.instance.pk:
            # el stock de un producto existente se cambia desde Inventario (entradas y salidas)
            del self.fields['stock_inicial']

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        repetido = Producto.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists()
        if repetido:
            raise forms.ValidationError('Ya existe un producto con ese nombre.')
        return nombre

    def clean_costo(self):
        return self.cleaned_data.get('costo') or 0

    def save(self, commit=True, usuario=None):
        """Al crear, el stock inicial entra como movimiento de Inventario ("Inventario inicial")."""
        from apps.inventario.servicios import registrar_entrada

        nuevo = not self.instance.pk
        producto = super().save(commit=False)
        if nuevo:
            producto.stock = 0
        if commit:
            producto.save()
            inicial = self.cleaned_data.get('stock_inicial') or 0
            if nuevo and producto.controla_stock and inicial > 0:
                registrar_entrada(producto_id=producto.pk, cantidad=inicial, usuario=usuario,
                                  costo=producto.costo, nota='Inventario inicial')
                producto.refresh_from_db(fields=['stock'])
        return producto
