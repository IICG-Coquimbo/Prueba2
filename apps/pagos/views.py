from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Pago
from .forms import PagoForm


class PagoListView(PermissionRequiredMixin, ListView):
    model = Pago
    template_name = "pagos/pago_list.html"
    context_object_name = "object_list"
    permission_required = "pagos.view_pago"


class PagoDetailView(PermissionRequiredMixin, DetailView):
    model = Pago
    template_name = "pagos/pago_detail.html"
    permission_required = "pagos.view_pago"


class PagoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = "pagos/pago_form.html"
    success_url = reverse_lazy("pagos:pago_list")
    success_message = "Pago creado correctamente."
    permission_required = "pagos.add_pago"


class PagoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Pago
    form_class = PagoForm
    template_name = "pagos/pago_form.html"
    success_url = reverse_lazy("pagos:pago_list")
    success_message = "Pago actualizado correctamente."
    permission_required = "pagos.change_pago"


class PagoDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Pago
    template_name = "pagos/pago_confirm_delete.html"
    success_url = reverse_lazy("pagos:pago_list")
    success_message = "Pago eliminado correctamente."
    permission_required = "pagos.delete_pago"
