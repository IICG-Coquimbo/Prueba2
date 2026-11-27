from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from apps.cuentas.models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Usuario'
        self.fields['password'].label = 'Contrasena'
        for campo in self.fields.values():
            campo.widget.attrs.update({'class': 'form-control'})


class RegistroForm(UserCreationForm):
    telefono = forms.CharField(
        max_length=20,
        label='Telefono',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email']
        labels = {
            'username': 'Usuario',
            'first_name': 'Nombre',
            'email': 'Correo electronico',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contrasena'
        self.fields['password2'].label = 'Confirmar contrasena'
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            PerfilCliente.objects.create(
                usuario=user,
                telefono=self.cleaned_data['telefono'],
            )
        return user


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ['alias', 'direccion', 'referencia']
        labels = {
            'alias': 'Alias',
            'direccion': 'Direccion',
            'referencia': 'Referencia',
        }
        widgets = {
            'alias': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['referencia'].required = False
