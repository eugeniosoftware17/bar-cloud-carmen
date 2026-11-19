from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import MODULOS
from .permisos import guardar_permisos, permisos_de

NIVEL_CHOICES = [('', 'Sin acceso'), ('ver', 'Solo ver'), ('editar', 'Ver y editar')]


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username', 'autocapitalize': 'none'}),
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Este usuario está desactivado. Habla con el administrador.',
    }


class UsuarioForm(forms.ModelForm):
    """Crear o editar un usuario y elegir, módulo por módulo, si no tiene acceso, solo ve o puede editar."""

    password1 = forms.CharField(label='Contraseña', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = forms.CharField(label='Repite la contraseña', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'is_active']
        labels = {'username': 'Usuario (para entrar)', 'first_name': 'Nombre', 'is_active': 'Activo (puede entrar al sistema)'}
        widgets = {
            'username': forms.TextInput(attrs={'autocapitalize': 'none', 'autocomplete': 'off', 'placeholder': 'Ej.: caja1'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Ej.: María Santos'}),
        }
        error_messages = {
            'username': {'unique': 'Ya existe un usuario con ese nombre.', 'required': 'Escribe el usuario.'},
        }

    def __init__(self, *args, actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual = actual
        u = self.instance
        actuales = permisos_de(u) if u.pk else {'venta_directa': 'editar', 'mesas': 'editar', 'productos': 'ver'}
        self.es_dueno = bool(u.pk and u.is_superuser)
        self.es_el_mismo = bool(u.pk and actual and u.pk == actual.pk)
        # los permisos del dueño y los tuyos propios no se cambian aquí
        bloqueado = self.es_dueno or self.es_el_mismo
        for clave, nombre, editar in MODULOS:
            self.fields[f'perm_{clave}'] = forms.ChoiceField(
                label=nombre, choices=NIVEL_CHOICES, required=False, initial=actuales.get(clave, ''),
                help_text=editar, disabled=bloqueado, widget=forms.RadioSelect,
            )
        if u.pk:
            del self.fields['password1'], self.fields['password2']
            if self.es_el_mismo or self.es_dueno:
                self.fields['is_active'].disabled = True
        else:
            self.fields['is_active'].initial = True

    @property
    def campos_permiso(self):
        return [(self[f'perm_{c}'], c) for c, _, _ in MODULOS]

    def clean_username(self):
        nombre = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe un usuario con ese nombre.')
        return nombre

    def clean(self):
        datos = super().clean()
        if 'password1' in self.fields:
            p1, p2 = datos.get('password1'), datos.get('password2')
            if p1 and p2 and p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            elif p1:
                try:
                    validate_password(p1, User(username=datos.get('username', ''), first_name=datos.get('first_name', '')))
                except forms.ValidationError as e:
                    self.add_error('password1', e)
        if not (self.es_dueno or self.es_el_mismo) and not any(datos.get(f'perm_{c}') for c, _, _ in MODULOS):
            raise forms.ValidationError('Dale acceso al menos a un módulo; si no, el usuario no podrá hacer nada.')
        return datos

    def save(self, commit=True):
        user = super().save(commit=False)
        if 'password1' in self.fields:
            user.set_password(self.cleaned_data['password1'])
        user.save()
        if not (self.es_dueno or self.es_el_mismo):
            guardar_permisos(user, {c: self.cleaned_data.get(f'perm_{c}') for c, _, _ in MODULOS})
        return user


class ClaveForm(SetPasswordForm):
    error_messages = {'password_mismatch': 'Las contraseñas no coinciden.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Contraseña nueva'
        self.fields['new_password1'].help_text = ''
        self.fields['new_password2'].label = 'Repite la contraseña'
