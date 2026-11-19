from django import forms
from django.utils import timezone

from .models import Gasto


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['concepto', 'monto', 'fecha', 'categoria']
        widgets = {
            'concepto': forms.TextInput(attrs={'maxlength': 60, 'autofocus': True, 'placeholder': 'Ej.: compra de limones'}),
            'monto': forms.NumberInput(attrs={'min': 1, 'step': 1, 'inputmode': 'numeric'}),
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
        error_messages = {
            'concepto': {'required': 'Escribe el concepto.'},
            'monto': {'required': 'Escribe el monto.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].widget.attrs['max'] = timezone.localdate().isoformat()

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha no puede ser futura.')
        return fecha
