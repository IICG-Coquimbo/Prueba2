from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import Pedido

LISTO_DESPACHO = Pedido.Estado.LISTO_DESPACHO
EN_CAMINO = Pedido.Estado.EN_CAMINO
ENTREGADO = Pedido.Estado.ENTREGADO


class EntregaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "entregas/entrega_list.html"
    context_object_name = "object_list"
    permission_required = "pedidos.despachar_pedido"

    def get_queryset(self):
        user = self.request.user
        return (
            Pedido.objects.select_related("cliente", "direccion", "entrega")
            .filter(
                Q(estado=LISTO_DESPACHO)
                | Q(entrega__repartidor=user, estado__in=[EN_CAMINO, ENTREGADO])
            )
            .distinct()
            .order_by("creado")
        )
