from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import Group
from django.contrib.auth import login
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, FormView
from django.shortcuts import redirect

from .forms import LoginForm, DireccionForm, RegistroForm
from .models import Direccion
from apps.cuentas.models import PerfilCliente
from django.contrib.auth.models import User


class CuentasLoginView(LoginView):
    form_class = LoginForm
    template_name = "cuentas/login.html"


class CuentasLogoutView(LogoutView):
    next_page = "cuentas:login"


class RegistroView(FormView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password1"],
        )
        PerfilCliente.objects.create(usuario=user, telefono="")
        grupo_cliente, _ = Group.objects.get_or_create(name="Cliente")
        user.groups.add(grupo_cliente)
        login(self.request, user)
        return redirect("inicio")


class DireccionListView(PermissionRequiredMixin, ListView):
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "object_list"
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada correctamente."
    permission_required = "cuentas.add_direccion"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada correctamente."
    permission_required = "cuentas.change_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion eliminada correctamente."
    permission_required = "cuentas.delete_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)
