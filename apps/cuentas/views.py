from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.cuentas.forms import DireccionForm, LoginForm, RegistroForm
from apps.cuentas.models import Direccion, PerfilCliente


class LoginView(AuthLoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class LogoutView(AuthLogoutView):
    pass


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        usuario = form.save()
        PerfilCliente.objects.create(
            usuario=usuario,
            telefono=form.cleaned_data["telefono"],
        )
        usuario.groups.add(Group.objects.get(name="Cliente"))
        login(self.request, usuario)
        messages.success(self.request, "Registro completado correctamente.")
        self.object = usuario
        return HttpResponseRedirect(self.get_success_url())


class DireccionListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionCreateView(
    PermissionRequiredMixin,
    LoginRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    permission_required = "cuentas.add_direccion"
    model = Direccion
    form_class = DireccionForm
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
    permission_required = "cuentas.change_direccion"
    model = Direccion
    form_class = DireccionForm
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección actualizada correctamente."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, LoginRequiredMixin, DeleteView):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    success_url = reverse_lazy("cuentas:direccion_list")
    template_name = "cuentas/direccion_confirm_delete.html"

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)
