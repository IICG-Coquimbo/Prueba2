from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class LoginView(AuthLoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class LogoutView(AuthLogoutView):
    pass


class RegistroView(SuccessMessageMixin, CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Tu cuenta fue creada correctamente."

    def form_valid(self, form):
        response = super().form_valid(form)
        PerfilCliente.objects.create(
            usuario=self.object,
            telefono=form.cleaned_data["telefono"],
        )
        grupo, _creado = Group.objects.get_or_create(name="Cliente")
        self.object.groups.add(grupo)
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        return response


class DireccionListView(PermissionRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "cuentas.add_direccion"
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada correctamente."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "cuentas.change_direccion"
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada correctamente."

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Direccion borrada correctamente.")
        return super().delete(request, *args, **kwargs)
