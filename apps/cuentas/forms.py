from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"
        self.fields["username"].label = "Usuario"
        self.fields["password"].label = "Contraseña"


class RegistroForm(forms.ModelForm):
    telefono = forms.CharField(
        max_length=20,
        label="Teléfono",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "password", "telefono"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["email"].required = True
        self.fields["username"].label = "Usuario"
        self.fields["first_name"].label = "Nombre"
        self.fields["email"].label = "Correo electrónico"
        self.fields["password"].label = "Contraseña"
        self.fields["telefono"].label = "Teléfono"
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["first_name"].widget.attrs["class"] = "form-control"
        self.fields["email"].widget.attrs["class"] = "form-control"
        self.fields["password"].widget = forms.PasswordInput(
            attrs={"class": "form-control"}
        )
        self.fields["telefono"].widget.attrs["class"] = "form-control"

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
            PerfilCliente.objects.create(
                usuario=usuario,
                telefono=self.cleaned_data["telefono"],
            )
        return usuario


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ["telefono"]
        labels = {"telefono": "Teléfono"}
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
            "referencia": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }
