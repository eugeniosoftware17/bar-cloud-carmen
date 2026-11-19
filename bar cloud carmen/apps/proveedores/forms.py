from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'contacto', 'telefono', 'suple', 'nota']
        widgets = {
            'nombre': forms.TextInput(attrs={'maxlength': 60, 'autofocus': True, 'placeholder': 'Ej.: Distribuidora del Cibao'}),
            'contacto': forms.TextInput(attrs={'placeholder': 'Ej.: Pedro Almonte'}),
            'telefono': forms.TextInput(attrs={'type': 'tel', 'inputmode': 'tel', 'placeholder': 'Ej.: 809-555-0201'}),
            'suple': forms.TextInput(attrs={'placeholder': 'Ej.: cerveza, refrescos'}),
            'nota': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej.: entrega martes y viernes'}),
        }
        error_messages = {'nombre': {'required': 'Escribe el nombre del proveedor.'}}

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        if Proveedor.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un proveedor con ese nombre.')
        return nombre
