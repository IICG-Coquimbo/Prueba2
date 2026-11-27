from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.cuentas.forms import DireccionForm, LoginForm, RegistroForm
from apps.cuentas.models import Direccion, PerfilCliente


class IniciarSesionView(LoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"
    redirect_authenticated_user = True


class CerrarSesionView(LogoutView):
    next_page = reverse_lazy("cuentas:login")


class RegistroView(CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        correo = form.cleaned_data["email"].strip().lower()
        usuario = form.save(commit=False)
        usuario.username = correo
        usuario.email = correo
        usuario.first_name = form.cleaned_data["nombre"].strip()
        usuario.set_password(form.cleaned_data["password1"])
        usuario.save()

        PerfilCliente.objects.create(
            usuario=usuario,
            telefono=form.cleaned_data["telefono"].strip(),
        )

        grupo_cliente, _ = Group.objects.get_or_create(name="Cliente")
        usuario.groups.add(grupo_cliente)

        login(self.request, usuario)
        messages.success(self.request, "Registro realizado con éxito.")
        return redirect(self.success_url)


class DireccionListView(PermissionRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user).order_by("alias")


class DireccionCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "cuentas.add_direccion"
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Dirección creada correctamente.")
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "cuentas.change_direccion"
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Dirección actualizada correctamente.")
        return super().form_valid(form)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Dirección eliminada correctamente.")
        return super().form_valid(form)
