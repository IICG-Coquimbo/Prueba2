from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import CreateView, View, ListView, DetailView, Update
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .models import PerfilCliente, Direccion
from .forms import LoginForm


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = "cuentas/login.html"


class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        # Django 5: LogoutView only accepts POST
        if request.method != "POST":
            return self.handle_http_not_supported(request)
        return super().dispatch(request, *args, **kwargs)


class RegistroView(CreateView):
    model = User
    template_name = "cuentas/registro.html"
    form_class = UserCreationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        # Create PerfilCliente
        PerfilCliente.objects.create(usuario=self.object)
        # Add to "Cliente" group
        cliente_group, _ = Group.objects.get_or_create(name="Cliente")
        self.object.groups.add(cliente_group)
        # Log the user in
        from django.contrib.auth import login
        login(self.request, self.object)
        return response

    def get_success_url(self):
        return reverse_lazy("inicio")
