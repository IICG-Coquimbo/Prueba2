from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    """RF-02: inicio de sesion con estilo Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"


class RegistroForm(UserCreationForm):
    """RF-01: registro de clientes con telefono de contacto."""

    telefono = forms.CharField(
        max_length=20,
        label="Telefono",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "email"]
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "email": "Correo electronico",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Contrasena"
        self.fields["password1"].widget = forms.PasswordInput(
            attrs={"class": "form-control"}
        )
        self.fields["password2"].label = "Confirmar contrasena"
        self.fields["password2"].widget = forms.PasswordInput(
            attrs={"class": "form-control"}
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            self.add_error("email", "Ya existe un usuario con ese correo electronico.")
        return email


class PerfilClienteForm(forms.ModelForm):
    """RF-01: editar el telefono del perfil del cliente."""

    class Meta:
        model = PerfilCliente
        fields = ["telefono"]
        labels = {"telefono": "Telefono"}
        widgets = {
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }


class DireccionForm(forms.ModelForm):
    """RF-06: alta y edicion de direcciones del cliente."""

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
