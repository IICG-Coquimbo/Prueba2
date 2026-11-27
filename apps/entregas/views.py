from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Pedido
    template_name = "entregas/entrega_list.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        return (
            Pedido.objects.select_related("cliente", "direccion")
            .prefetch_related("items__producto", "items__opciones")
            .filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO)
                | Q(estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO], entrega__repartidor=user)
            )
            .order_by("-creado")
        )
