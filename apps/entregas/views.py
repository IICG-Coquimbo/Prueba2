from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView
from django.db import models
from apps.pedidos.models import Pedido


class EntregaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "entregas/entrega_list.html"
    context_object_name = "pedidos"
    paginate_by = 10
    permission_required = "pedidos.despachar_pedido"

    def get_queryset(self):
        qs = Pedido.objects.select_related("cliente", "direccion", "entrega__repartidor").prefetch_related("items__producto")
        user = self.request.user
        qs = qs.filter(
            models.Q(estado=Pedido.Estado.LISTO_DESPACHO) |
            models.Q(estado=Pedido.Estado.EN_CAMINO, entrega__repartidor=user) |
            models.Q(estado=Pedido.Estado.ENTREGADO, entrega__repartidor=user)
        ).order_by("creado")
        return qs