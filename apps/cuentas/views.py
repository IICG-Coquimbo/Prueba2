from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, RegistroForm
from .models import Direccion, PerfilCliente


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password1"])
        user.save()
        grupo, _ = Group.objects.get_or_create(name="Cliente")
        user.groups.add(grupo)
        PerfilCliente.objects.create(
            usuario=user, telefono=form.cleaned_data["telefono"]
        )
        login(self.request, user)
        return super().form_valid(form)


class DireccionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    model = Direccion
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion creada correctamente"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    model = Direccion
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion actualizada correctamente"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Direccion eliminada correctamente"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)
