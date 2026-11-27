from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from apps.cuentas.models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class RegistroForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text=""
    )
    telefono = forms.CharField(
        max_length=20,
        label="Teléfono",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+56 9 1234 5678"})
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Nombre de usuario",
            "email": "Correo electrónico",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            PerfilCliente.objects.create(usuario=user, telefono=self.cleaned_data["telefono"])
        return user


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ["alias", "direccion", "referencia"]
        labels = {
            "alias": "Alias (ej. Casa, Trabajo)",
            "direccion": "Direccion",
            "referencia": "Referencia (opcional)",
        }
        widgets = {
            "alias": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
        }