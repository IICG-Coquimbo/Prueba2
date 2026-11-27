from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import Pedido


class EntregaListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Pedido
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        return (
            Pedido.objects.filter(
                Q(estado="listo_despacho")
                | Q(
                    estado__in=["en_camino", "entregado"],
                    entrega__repartidor=self.request.user,
                )
            )
            .order_by("creado")
        )
