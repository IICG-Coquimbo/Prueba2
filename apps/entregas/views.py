from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView

from .models import Entrega


class EntregaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pedidos.despachar_pedido"
    model = Entrega
    template_name = "entregas/entrega_list.html"
    context_object_name = "entregas"

    def get_queryset(self):
        user = self.request.user
        return self.model.objects.filter(
            pedido__estado="listo_despacho"
        ) | self.model.objects.filter(
            pedido__estado__in=["en_camino", "entregado"], repartidor=user
        )
