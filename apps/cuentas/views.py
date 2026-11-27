from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, UserForm
from .models import Direccion


class RegistroView(SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Tu cuenta fue creada correctamente."

    def form_valid(self, form):
        response = super().form_valid(form)
        grupo, _creado = Group.objects.get_or_create(name="Cliente")
        self.object.groups.add(grupo)
        login(
            self.request,
            self.object,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return response


class LoginView(AuthLoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class LogoutView(AuthLogoutView):
    pass


class DireccionListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionCreateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    permission_required = "cuentas.add_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección creada correctamente."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    permission_required = "cuentas.change_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección actualizada correctamente."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionDeleteView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    permission_required = "cuentas.delete_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección eliminada correctamente."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)
