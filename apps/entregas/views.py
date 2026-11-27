from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import EstadoPedido, Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Pedido
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        return (
            Pedido.objects.select_related("cliente", "direccion", "entrega")
            .prefetch_related("items__producto", "items__opciones")
            .filter(
                Q(estado=EstadoPedido.LISTO_DESPACHO)
                | Q(
                    estado__in=[EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO],
                    entrega__repartidor=self.request.user,
                )
            )
            .order_by("-creado")
        )
