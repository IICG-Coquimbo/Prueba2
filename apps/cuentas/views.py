from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import CharField, TextInput
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DireccionForm, LoginForm
from .models import Direccion, PerfilCliente


class RegistroForm(UserCreationForm):
    """Registro publico: crea el User (con contrasena hasheada) y su telefono."""

    telefono = CharField(
        label="Teléfono",
        max_length=20,
        widget=TextInput(attrs={"class": "form-control"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        for campo in self.fields.values():
            campo.widget.attrs.update({"class": "form-control"})


class LoginView(DjangoLoginView):
    authentication_form = LoginForm
    template_name = "cuentas/login.html"


class LogoutView(DjangoLogoutView):
    """Django 5: solo POST; la plantilla usa un formulario con csrf_token."""


class RegistroView(SuccessMessageMixin, CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("inicio")
    success_message = "Registro exitoso. Bienvenido a Cafe Rincon."

    def form_valid(self, form):
        usuario = form.save()
        PerfilCliente.objects.create(
            usuario=usuario,
            telefono=form.cleaned_data["telefono"],
        )
        grupo_cliente, _creado = Group.objects.get_or_create(name="Cliente")
        usuario.groups.add(grupo_cliente)
        login(self.request, usuario)
        return super().form_valid(form)


class DireccionListView(PermissionRequiredMixin, ListView):
    model = Direccion
    permission_required = "cuentas.view_direccion"

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Direccion
    form_class = DireccionForm
    permission_required = "cuentas.add_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección creada correctamente."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Direccion
    form_class = DireccionForm
    permission_required = "cuentas.change_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")
    success_message = "Dirección actualizada correctamente."

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    model = Direccion
    permission_required = "cuentas.delete_direccion"
    success_url = reverse_lazy("cuentas:direccion_list")

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)
