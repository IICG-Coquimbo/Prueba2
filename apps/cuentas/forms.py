from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Direccion, PerfilCliente


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ["telefono"]
        labels = {"telefono": "Teléfono"}
        widgets = {
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        if not telefono:
            raise forms.ValidationError("Ingrese un teléfono.")
        return telefono


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["alias", "direccion", "referencia"]
        labels = {
            "alias": "Alias (Casa, Trabajo...)",
            "direccion": "Dirección",
            "referencia": "Referencia",
        }
        widgets = {
            "alias": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_alias(self):
        alias = self.cleaned_data["alias"].strip()
        if not alias:
            raise forms.ValidationError("Ingrese un alias para la dirección.")
        return alias

    def clean_direccion(self):
        direccion = self.cleaned_data["direccion"].strip()
        if not direccion:
            raise forms.ValidationError("Ingrese la dirección.")
        return direccion


class LoginForm(AuthenticationForm):
    """Inicio de sesión con etiquetas en español y estilo Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contraseña"
        for campo in self.fields.values():
            campo.widget.attrs.update({"class": "form-control"})
