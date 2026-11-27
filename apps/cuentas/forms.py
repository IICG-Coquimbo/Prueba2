from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


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
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contrasena"
        for campo in self.fields.values():
            campo.widget.attrs.update({"class": "form-control"})


class RegistroForm(UserCreationForm):
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
            "email": "Correo",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Contrasena"
        self.fields["password2"].label = "Confirmar contrasena"
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def clean_email(self):
        correo = self.cleaned_data.get("email", "").strip()
        if not correo:
            self.add_error("email", "El correo es obligatorio.")
            return correo
        if User.objects.filter(email__iexact=correo).exists():
            self.add_error("email", "Ya existe un usuario con este correo.")
        return correo
