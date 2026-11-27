from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class RegistroView(CreateView, SuccessMessageMixin):
    """RF-01: registro publico de clientes, con perfil y grupo Cliente."""

    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        user = form.save()
        PerfilCliente.objects.create(
            usuario=user,
            telefono=form.cleaned_data["telefono"],
        )
        grupo, _creado = Group.objects.get_or_create(name="Cliente")
        user.groups.add(grupo)
        login(self.request, user)
        messages.success(self.request, "Tu cuenta fue creada. Bienvenido a Cafe Rincon.")
        return HttpResponseRedirect(self.get_success_url())


class LoginView(AuthLoginView):
    """RF-02: inicio de sesion con el formulario de la app."""

    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class LogoutView(AuthLogoutView):
    """Cierre de sesion: Django 5 solo acepta POST."""


class DireccionListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    """RF-06: cada cliente ve solo sus direcciones."""

    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    """RF-06: alta de una direccion para el usuario en sesion."""

    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada correctamente."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """RF-06: edicion de una direccion propia."""

    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada correctamente."

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    """RF-06: borrado de una direccion propia."""

    permission_required = "cuentas.delete_direccion"
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion borrada correctamente."

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)
