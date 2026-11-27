from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class CuentaLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"
    redirect_authenticated_user = False


class CuentaLogoutView(LogoutView):
    pass


class RegistroView(SuccessMessageMixin, CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Tu cuenta fue creada."

    def form_valid(self, form):
        response = super().form_valid(form)
        usuario = form.instance
        PerfilCliente.objects.create(
            usuario=usuario,
            telefono=form.cleaned_data["telefono"],
        )
        grupo, _ = Group.objects.get_or_create(name="Cliente")
        usuario.groups.add(grupo)
        login(self.request, usuario)
        return response


class DireccionListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionCreateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    model = Direccion
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    model = Direccion
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionDeleteView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion eliminada."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)
