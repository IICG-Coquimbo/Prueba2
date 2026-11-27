from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import Pedido
from apps.pedidos.views import PERMISO_DESPACHAR, PedidoVisibleMixin


class EntregaListView(PermissionRequiredMixin, PedidoVisibleMixin, ListView):
    permission_required = PERMISO_DESPACHAR
    model = Pedido
    template_name = "entregas/entrega_list.html"

    def get_queryset(self):
        # Los pedidos listos aún no tienen una Entrega.
        estado = Pedido.Estado
        listos = Q(estado=estado.LISTO_DESPACHO)
        propios = Q(
            estado__in=(estado.EN_CAMINO, estado.ENTREGADO),
            entrega__repartidor=self.request.user,
        )
        return (
            super().get_queryset().filter(listos | propios)
            .select_related("entrega", "direccion", "cliente__perfil")
            .prefetch_related("items__producto", "items__opciones")
            .order_by("creado", "pk")
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["pedidos_con_avance"] = {
            pedido.pk for pedido in contexto["object_list"] if self.puede_avanzar(pedido)
        }
        return contexto
