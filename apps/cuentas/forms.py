from django.contrib.auth.forms import AuthenticationForm
from django import forms

from apps.cuentas.models import Direccion, PerfilCliente


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ["telefono"]
        labels = {
            "telefono": "Telefono",
        }
        widgets = {
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "").strip()
        digitos = "".join(caracter for caracter in telefono if caracter.isdigit())
        if not digitos:
            raise forms.ValidationError("El telefono debe contener al menos un numero.")
        return telefono


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["alias", "direccion", "referencia"]
        labels = {
            "alias": "Alias",
            "direccion": "Direccion",
            "referencia": "Referencia",
        }
        widgets = {
            "alias": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
        }


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields:
            self.fields[campo].widget.attrs.update({"class": "form-control"})
