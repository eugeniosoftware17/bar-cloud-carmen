from django import forms

from .models import Configuracion


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = [
            'nombre', 'direccion', 'telefono',
            'cobrar_propina', 'propina_porcentaje', 'cobrar_itbis', 'itbis_porcentaje',
            'recibo_mostrar_atendio', 'recibo_mensaje', 'recibo_mostrar_aviso', 'recibo_aviso',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej.: Bar de Carmen'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Ej.: Santiago, Rep. Dominicana'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej.: 809-555-0101', 'inputmode': 'tel'}),
            'propina_porcentaje': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'inputmode': 'decimal'}),
            'itbis_porcentaje': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01', 'inputmode': 'decimal'}),
            'recibo_mensaje': forms.TextInput(attrs={'placeholder': 'Déjalo vacío para no mostrarlo'}),
            'recibo_aviso': forms.TextInput(),
        }
        labels = {'nombre': 'Nombre que sale en la factura'}
        error_messages = {'nombre': {'required': 'Escribe el nombre que saldrá en la factura.'}}
