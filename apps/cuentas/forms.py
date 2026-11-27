from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nombre de usuario"
        self.fields["password"].label = "Contraseña"
        for field in self.fields.values():
            classes = field.widget.attrs.get("class", "").split()
            if "form-control" not in classes:
                classes.append("form-control")
            field.widget.attrs["class"] = " ".join(classes)


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


class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        label="Correo",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    first_name = forms.CharField(
        label="Nombre",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Apellido",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nombre de usuario"
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["password1"].widget.attrs["class"] = "form-control"
        self.fields["password2"].widget.attrs["class"] = "form-control"
