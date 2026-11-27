from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import PerfilCliente, Direccion


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields:
            self.fields[campo].widget.attrs.update({"class": "form-control"})


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ["usuario", "telefono"]
        labels = {
            "usuario": "Usuario",
            "telefono": "Teléfono",
        }
        widgets = {
            "usuario": forms.Select(attrs={"class": "form-select"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if not telefono:
            raise forms.ValidationError("El teléfono es obligatorio.")
        return telefono


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

    def clean_alias(self):
        alias = self.cleaned_data.get("alias")
        if not alias:
            raise forms.ValidationError("El alias es obligatorio.")
        return alias


class RegistroForm(forms.Form):
    username = forms.CharField(
        label="Usuario de acceso",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.TextInput(attrs={"class": "form-control", "type": "password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.TextInput(attrs={"class": "form-control", "type": "password"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return cleaned
