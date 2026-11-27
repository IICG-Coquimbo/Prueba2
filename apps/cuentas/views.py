from django.contrib.auth import login
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


class LoginView(DjangoLoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class RegistroView(SuccessMessageMixin, CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Tu cuenta se creó correctamente."

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            PerfilCliente.objects.create(
                usuario=self.object, telefono=form.cleaned_data["telefono"]
            )
            # El registro puede preceder a la instalación de permisos con crear_roles.
            grupo, _ = Group.objects.get_or_create(name="Cliente")
            self.object.groups.add(grupo)

        login(self.request, self.object)
        return response


class DireccionesPropiasMixin:
    model = Direccion

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionListView(PermissionRequiredMixin, DireccionesPropiasMixin, ListView):
    permission_required = "cuentas.view_direccion"
    ordering = ("alias", "pk")


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Direccion
    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "La dirección se agregó correctamente."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(
    PermissionRequiredMixin, DireccionesPropiasMixin, SuccessMessageMixin, UpdateView
):
    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "La dirección se actualizó correctamente."


class DireccionDeleteView(
    PermissionRequiredMixin, DireccionesPropiasMixin, SuccessMessageMixin, DeleteView
):
    permission_required = "cuentas.delete_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "La dirección se borró correctamente."
