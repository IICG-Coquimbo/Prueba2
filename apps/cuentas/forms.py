from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    telefono = forms.CharField(max_length=20, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "telefono")


class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ("alias", "direccion", "referencia")
