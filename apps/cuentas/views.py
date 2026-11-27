"""Vistas de la app cuentas segun docs/reglas_usuarios.md y docs/roles.md."""

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class CuentaLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class CuentaLogoutView(LogoutView):
    next_page = "cuentas:login"


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("instance", None)
        return kwargs

    def form_valid(self, form):
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password1"],
        )
        grupo_cliente = Group.objects.get(name="Cliente")
        user.groups.add(grupo_cliente)
        PerfilCliente.objects.create(
            usuario=user,
            telefono=form.cleaned_data["telefono"],
        )
        login(self.request, user)
        return HttpResponseRedirect(self.get_success_url())


class DireccionListView(
    LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView
):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.add_direccion"
    success_message = "Direccion creada correctamente."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.change_direccion"
    success_message = "Direccion actualizada correctamente."

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.delete_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)
