from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.models import User, Group
from django.contrib import messages
from apps.cuentas.models import Direccion
from apps.cuentas.forms import LoginForm, DireccionForm, RegistroForm
from apps.cuentas.models import PerfilCliente


class CustomLoginView(LoginView):
    template_name = "cuentas/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class CustomLogoutView(LoginRequiredMixin, LogoutView):
    next_page = reverse_lazy("cuentas:login")


class RegistroView(CreateView):
    model = User
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        user = form.save()
        grupo_cliente = Group.objects.get(name="Cliente")
        user.groups.add(grupo_cliente)
        messages.success(self.request, "Registro exitoso. Bienvenido!")
        return super().form_valid(form)


class DireccionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.add_direccion"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Direccion creada.")
        return super().form_valid(form)


class DireccionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Direccion
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.change_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Direccion actualizada.")
        return super().form_valid(form)


class DireccionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    permission_required = "cuentas.delete_direccion"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Direccion eliminada.")
        return super().form_valid(form)