from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import DireccionForm, LoginForm, RegistroForm
from .models import Direccion, PerfilCliente


PERMISOS_CLIENTE = [
    ("catalogo", "categoria", ["view_categoria"]),
    ("catalogo", "producto", ["view_producto"]),
    ("pedidos", "pedido", ["view_pedido", "add_pedido", "change_pedido"]),
    ("pedidos", "itempedido", ["view_itempedido", "add_itempedido", "change_itempedido", "delete_itempedido"]),
    ("cuentas", "direccion", ["view_direccion", "add_direccion", "change_direccion", "delete_direccion"]),
]


class CuentasLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class CuentasLogoutView(LogoutView):
    pass


class RegistroView(CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Registro completado."

    @transaction.atomic
    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password1"])
        user.save()
        PerfilCliente.objects.update_or_create(
            usuario=user,
            defaults={"telefono": form.cleaned_data["telefono"]},
        )
        grupo, _creado = Group.objects.get_or_create(name="Cliente")
        permisos = []
        for app_label, model, codenames in PERMISOS_CLIENTE:
            permisos.extend(
                Permission.objects.filter(
                    content_type__app_label=app_label,
                    content_type__model=model,
                    codename__in=codenames,
                )
            )
        grupo.permissions.add(*permisos)
        user.groups.add(grupo)
        login(self.request, user)
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())


class DireccionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user).order_by("alias", "pk")


class DireccionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    permission_required = "cuentas.add_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección creada."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
