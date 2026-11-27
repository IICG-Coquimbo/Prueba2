from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from apps.cuentas.models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.update({"class": "form-control"})


class RegistroForm(forms.Form):
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["alias", "direccion", "referencia"]
        labels = {
            "alias": "Alias",
            "direccion": "Dirección",
            "referencia": "Referencia",
        }
        widgets = {
            "alias": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
        }


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ["telefono"]
        labels = {
            "telefono": "Teléfono",
        }
        widgets = {
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }
