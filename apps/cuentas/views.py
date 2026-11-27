from django.contrib.auth import login
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class CuentaLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class CuentaLogoutView(LogoutView):
    pass


class RegistroView(SuccessMessageMixin, CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Cuenta creada."

    def form_valid(self, form):
        usuario = form.save()
        PerfilCliente.objects.create(
            usuario=usuario, telefono=form.cleaned_data["telefono"]
        )
        grupo, _ = Group.objects.get_or_create(name="Cliente")
        usuario.groups.add(grupo)
        login(self.request, usuario)
        return super().form_valid(form)


class DireccionListView(PermissionRequiredMixin, ListView):
    model = Direccion
    permission_required = "cuentas.view_direccion"
    template_name = "cuentas/direccion_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Direccion
    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Direccion
    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    model = Direccion
    permission_required = "cuentas.delete_direccion"
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)
