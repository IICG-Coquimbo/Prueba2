from django.views.generic import ListView
from django.contrib.auth.mixins import PermissionRequiredMixin

from .models import Entrega


class EntregaListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Entrega
    template_name = "entregas/entrega_list.html"
    context_object_name = "entregas"

    def get_queryset(self):
        user = self.request.user
        qs = Entrega.objects.select_related("pedido", "repartidor")
        if user.is_staff:
            return qs.all()
        if user.has_perm("pedidos.despachar_pedido"):
            # Repartidor: pedidos listo_despacho, y en_camino/entregado que son suyos
            from apps.pedidos.models import Pedido
            estados_repartidor = [
                Pedido.ESTADO_LISTO_DESPACHO,
                Pedido.ESTADO_EN_CAMINO,
                Pedido.ESTADO_ENTREGADO,
            ]
            return qs.filter(
                pedido__estado__in=estados_repartidor,
                repartidor=user,
            ).union(
                qs.filter(pedido__estado=Pedido.ESTADO_LISTO_DESPACHO)
            ).distinct().order_by("pedido__creado")
        return qs.none()
