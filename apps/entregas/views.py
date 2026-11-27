from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.pedidos.models import Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "entregas/entrega_list.html"
    permission_required = "pedidos.despachar_pedido"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        return Pedido.objects.select_related("cliente", "direccion", "entrega__repartidor").prefetch_related(
            "items__producto", "items__opciones"
        ).filter(
            Q(estado="listo_despacho") | Q(estado__in=["en_camino", "entregado"], entrega__repartidor=user)
        ).distinct().order_by("-creado")
