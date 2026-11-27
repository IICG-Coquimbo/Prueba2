from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import EstadoPedido, Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Pedido
    permission_required = "pedidos.despachar_pedido"
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        """Listo despacho y los propios del repartidor (RF-13)."""
        return (
            Pedido.objects.filter(
                Q(estado=EstadoPedido.LISTO_DESPACHO)
                | Q(
                    estado__in=(EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO),
                    entrega__repartidor=self.request.user,
                )
            )
            .select_related("cliente", "direccion", "entrega")
            .prefetch_related("items")
            .order_by("estado", "creado", "pk")
        )
