from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from .forms import RegistroForm, PerfilClienteForm, DireccionForm
from .models import PerfilCliente, Direccion


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password1"])
        user.save()
        grupo_cliente = Group.objects.get(name="Cliente")
        user.groups.add(grupo_cliente)
        PerfilCliente.objects.create(
            usuario=user,
            telefono=form.cleaned_data.get("telefono", ""),
        )
        login(self.request, user)
        messages.success(self.request, "Registro completado. Bienvenido a Cafe Rincon.")
        return redirect("inicio")


class DireccionListView(PermissionRequiredMixin, ListView):
    permission_required = "cuentas.view_direccion"
    model = Direccion
    template_name = "cuentas/direccion_list.html"
    context_object_name = "direcciones"

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "cuentas.add_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Direccion creada.")
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "cuentas.change_direccion"
    form_class = DireccionForm
    template_name = "cuentas/direccion_form.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Direccion actualizada.")
        return super().form_valid(form)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "cuentas.delete_direccion"
    model = Direccion
    template_name = "cuentas/direccion_confirm_delete.html"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Direccion eliminada.")
        return super().delete(request, *args, **kwargs)
