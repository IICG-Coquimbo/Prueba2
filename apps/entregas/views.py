"""Vistas de la app entregas segun docs/reglas_vistas_templates.md y docs/reglas_flujo.md."""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from apps.pedidos.models import Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "entregas/entrega_list.html"
    context_object_name = "pedidos"
    permission_required = "pedidos.despachar_pedido"

    def get_queryset(self):
        user = self.request.user
        # Repartidor: los listo_despacho, y los en_camino y entregado que sean suyos
        from apps.entregas.models import Entrega

        entregas_suyas = Entrega.objects.filter(repartidor=user).values_list(
            "pedido_id", flat=True
        )
        return Pedido.objects.filter(
            estado=Pedido.Estado.LISTO_DESPACHO
        ).union(
            Pedido.objects.filter(
                estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                pk__in=entregas_suyas,
            )
        ).order_by("-creado")
