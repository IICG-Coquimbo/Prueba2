from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import EstadoPedido, Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Pedido
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        user = self.request.user
        return (
            Pedido.objects.filter(
                Q(estado=EstadoPedido.LISTO_DESPACHO)
                | Q(
                    estado__in=[EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO],
                    entrega__repartidor=user,
                )
            )
            .select_related("cliente", "direccion")
            .distinct()
            .order_by("creado")
        )
