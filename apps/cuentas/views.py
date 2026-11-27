from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, RegistroForm
from .models import PerfilCliente

User = get_user_model()


class RegistroView(SuccessMessageMixin, CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Cuenta creada correctamente. Bienvenido."

    @transaction.atomic
    def form_valid(self, form):
        correo = form.cleaned_data["correo"]
        usuario = User.objects.create_user(
            username=correo,
            email=correo,
            first_name=form.cleaned_data["nombre"],
            password=form.cleaned_data["contrasena"],
        )
        PerfilCliente.objects.create(
            usuario=usuario,
            telefono=form.cleaned_data["telefono"],
        )
        grupo_cliente, _ = Group.objects.get_or_create(name="Cliente")
        usuario.groups.add(grupo_cliente)
        login(self.request, usuario)
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class CuentasLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class CuentasLogoutView(LogoutView):
    pass
