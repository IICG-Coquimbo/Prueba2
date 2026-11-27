from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.entregas.models import Entrega


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Entrega
    permission_required = "pedidos.despachar_pedido"
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        usuario = self.request.user
        return (
            Entrega.objects.select_related("pedido", "repartidor")
            .filter(
                Q(pedido__estado="listo_despacho")
                | Q(
                    repartidor=usuario,
                    pedido__estado__in=["en_camino", "entregado"],
                )
            )
            .distinct()
        )
