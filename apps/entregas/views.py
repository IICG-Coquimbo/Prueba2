from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import models
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Entrega
from .forms import EntregaForm


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Entrega
    template_name = "entregas/entrega_list.html"
    context_object_name = "object_list"
    permission_required = "pedidos.despachar_pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Entrega.objects.all()
        # Repartidor: listo_despacho (todos) y en_camino/entregado que sean suyos
        if user.has_perm("pedidos.despachar_pedido") and not user.has_perm("pedidos.ver_reportes"):
            qs = qs.filter(
                models.Q(pedido__estado="listo_despacho") |
                models.Q(pedido__estado__in=["en_camino", "entregado"], repartidor=user)
            ).distinct()
        return qs


class EntregaDetailView(PermissionRequiredMixin, DetailView):
    model = Entrega
    template_name = "entregas/entrega_detail.html"
    permission_required = "pedidos.despachar_pedido"


class EntregaCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Entrega
    form_class = EntregaForm
    template_name = "entregas/entrega_form.html"
    success_url = reverse_lazy("entregas:entrega_list")
    success_message = "Entrega creada correctamente."
    permission_required = "pedidos.despachar_pedido"


class EntregaUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Entrega
    form_class = EntregaForm
    template_name = "entregas/entrega_form.html"
    success_url = reverse_lazy("entregas:entrega_list")
    success_message = "Entrega actualizada correctamente."
    permission_required = "pedidos.despachar_pedido"


class EntregaDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Entrega
    template_name = "entregas/entrega_confirm_delete.html"
    success_url = reverse_lazy("entregas:entrega_list")
    success_message = "Entrega eliminada correctamente."
    permission_required = "pedidos.despachar_pedido"
