from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"


class RegistroForm(forms.Form):
    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)

    nombre = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    correo = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    contrasena = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()
        if User.objects.filter(email__iexact=correo).exists() or User.objects.filter(
            username__iexact=correo
        ).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return correo
