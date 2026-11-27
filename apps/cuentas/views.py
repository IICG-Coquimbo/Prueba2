from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.cuentas.forms import DireccionForm, LoginForm, RegistroForm
from apps.cuentas.models import Direccion


class LoginView(AuthLoginView):
    authentication_form = LoginForm
    template_name = 'cuentas/login.html'


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = 'cuentas/registro.html'
    success_url = reverse_lazy('inicio')

    def form_valid(self, form):
        user = form.save()
        grupo = Group.objects.get(name='Cliente')
        user.groups.add(grupo)
        login(self.request, user)
        messages.success(self.request, 'Tu cuenta ha sido creada. Bienvenido a Cafe Rincon.')
        self.object = user
        return HttpResponseRedirect(self.get_success_url())


class DireccionListView(PermissionRequiredMixin, ListView):
    permission_required = 'cuentas.view_direccion'
    model = Direccion
    template_name = 'cuentas/direccion_list.html'
    context_object_name = 'direcciones'

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user).order_by('alias')


class DireccionCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'cuentas.add_direccion'
    form_class = DireccionForm
    template_name = 'cuentas/direccion_form.html'
    success_url = reverse_lazy('cuentas:direccion_list')
    success_message = 'Direccion creada correctamente.'

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'cuentas.change_direccion'
    form_class = DireccionForm
    template_name = 'cuentas/direccion_form.html'
    success_url = reverse_lazy('cuentas:direccion_list')
    success_message = 'Direccion actualizada correctamente.'

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'cuentas.delete_direccion'
    model = Direccion
    template_name = 'cuentas/direccion_confirm_delete.html'
    success_url = reverse_lazy('cuentas:direccion_list')

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)
