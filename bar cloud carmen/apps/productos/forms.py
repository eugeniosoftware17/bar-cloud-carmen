from django import forms

from .models import ComboItem, Producto


class ComponenteForm(forms.ModelForm):
    class Meta:
        model = ComboItem
        fields = ['producto', 'cantidad']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'}),
        }
        error_messages = {
            'producto': {'required': 'Elige el producto.'},
            'cantidad': {'required': 'Escribe la cantidad.', 'min_value': 'Mínimo 1.'},
        }

    def __init__(self, *args, combo=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Producto.objects.filter(es_combo=False).order_by('nombre')
        if combo is not None and combo.pk:
            qs = qs.exclude(pk=combo.pk)
        self.fields['producto'].queryset = qs
        self.fields['producto'].empty_label = 'Elige un producto…'
        self.fields['producto'].label_from_instance = lambda p: p.nombre + ('' if p.activo else ' (desactivado)')

    def validate_unique(self):
        """Los repetidos se revisan en ProductoForm (con un mensaje claro) y las filas se guardan de nuevo."""


class BaseComponentes(forms.BaseInlineFormSet):
    def clean(self):
        """Igual que arriba: los repetidos los avisa ProductoForm."""


ComponentesFormSet = forms.inlineformset_factory(
    Producto, ComboItem, form=ComponenteForm, formset=BaseComponentes, fk_name='combo', extra=0, can_delete=True,
)


class ProductoForm(forms.ModelForm):
    stock_inicial = forms.IntegerField(label='Stock inicial', min_value=0, initial=0, required=False)

    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'costo', 'stock_minimo',
                  'es_combo', 'controla_stock', 'activo', 'foto']
        widgets = {
            'nombre': forms.TextInput(attrs={'maxlength': 40, 'placeholder': 'Ej.: Cerveza Presidente', 'autofocus': True}),
            'precio': forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'}),
            'costo': forms.NumberInput(attrs={'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'stock_minimo': forms.NumberInput(attrs={'min': 0, 'step': 1, 'inputmode': 'numeric'}),
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
        self.fields['stock_minimo'].required = False
        if self.instance.pk:
            # el stock de un producto existente se cambia desde Inventario (entradas y salidas)
            del self.fields['stock_inicial']
        self.componentes = ComponentesFormSet(
            data=self.data if self.is_bound else None, instance=self.instance, prefix='comp',
            form_kwargs={'combo': self.instance},
        )
        self.items_combo = []

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        repetido = Producto.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists()
        if repetido:
            raise forms.ValidationError('Ya existe un producto con ese nombre.')
        return nombre

    def clean_costo(self):
        return self.cleaned_data.get('costo') or 0

    def clean_stock_minimo(self):
        return self.cleaned_data.get('stock_minimo') or 0

    def clean(self):
        datos = super().clean()
        if not datos.get('es_combo'):
            return datos
        # self.instance todavía tiene los valores de antes de este cambio
        if self.instance.pk and not self.instance.es_combo:
            if self.instance.stock:
                raise forms.ValidationError(
                    f'Este producto tiene {self.instance.stock} en inventario. Ajusta el stock a 0 en Inventario '
                    'o crea el combo como un producto nuevo.')
            if self.instance.en_combos.exists():
                raise forms.ValidationError('Este producto forma parte de un combo, así que no puede ser un combo.')
        if not self.componentes.is_valid():
            raise forms.ValidationError('Revisa los productos del combo.')
        items = [f.cleaned_data for f in self.componentes.forms
                 if f.cleaned_data and not f.cleaned_data.get('DELETE') and f.cleaned_data.get('producto')]
        if not items:
            raise forms.ValidationError('Agrega al menos un producto al combo.')
        ids = [i['producto'].pk for i in items]
        if len(set(ids)) != len(ids):
            raise forms.ValidationError('Un producto está repetido en el combo: déjalo una sola vez y súmale la cantidad.')
        self.items_combo = items
        return datos

    def save(self, commit=True, usuario=None):
        """Al crear, el stock inicial entra como movimiento de Inventario ("Inventario inicial").

        Un combo no tiene stock propio: su costo es la suma de lo que lleva y su inventario es el de esos productos.
        """
        from apps.inventario.servicios import registrar_entrada

        nuevo = not self.instance.pk
        producto = super().save(commit=False)
        if nuevo:
            producto.stock = 0
        if producto.es_combo:
            producto.controla_stock = False
            producto.stock_minimo = 0
            producto.costo = sum((i['producto'].costo * i['cantidad'] for i in self.items_combo), 0)
        if commit:
            producto.save()
            producto.componentes.all().delete()
            if producto.es_combo:
                ComboItem.objects.bulk_create([
                    ComboItem(combo=producto, producto=i['producto'], cantidad=i['cantidad']) for i in self.items_combo
                ])
            inicial = self.cleaned_data.get('stock_inicial') or 0
            if nuevo and producto.controla_stock and inicial > 0:
                registrar_entrada(producto_id=producto.pk, cantidad=inicial, usuario=usuario,
                                  costo=producto.costo, nota='Inventario inicial')
                producto.refresh_from_db(fields=['stock'])
        return producto
