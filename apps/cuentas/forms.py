from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Direccion, PerfilCliente


User = get_user_model()


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario o correo electrónico"
        self.fields["password"].label = "Contraseña"
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class RegistroForm(UserCreationForm):
    """Crea el usuario; el alta de su perfil y grupo corresponde a RegistroView."""

    first_name = forms.CharField(
        label="Nombre",
        max_length=User._meta.get_field("first_name").max_length,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=User._meta.get_field("username").max_length,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=PerfilCliente._meta.get_field("telefono").max_length,
        widget=forms.TextInput(attrs={"class": "form-control", "type": "tel"}),
    )
    field_order = ["first_name", "email", "telefono", "password1", "password2"]

    class Meta:
        model = User
        fields = ["first_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        for nombre in ("password1", "password2"):
            self.fields[nombre].widget.attrs["class"] = "form-control"

    def clean_email(self):
        correo = self.cleaned_data["email"]
        # El correo es también el identificador de acceso del cliente.
        try:
            self.instance.username = User._meta.get_field("username").clean(
                correo, self.instance
            )
        except ValidationError as error:
            raise ValidationError(
                "Este correo contiene caracteres que no se pueden usar para iniciar sesión."
            ) from error

        if User.objects.filter(
            Q(email__iexact=correo) | Q(username__iexact=correo)
        ).exists():
            raise ValidationError("Ya existe una cuenta con este correo electrónico.")
        return correo


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
