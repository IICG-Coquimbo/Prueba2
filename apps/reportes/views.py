from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy

from pedidos.servicios import ventas_periodo, productos_mas_pedidos, ranking_repartidores


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    """Panel de reportes con ventas y productos más pedidos."""
    template_name = 'reportes/panel.html'
    permission_required = 'pedidos.ver_reportes'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ventas_hoy'] = ventas_periodo(dias=1)
        ctx['ventas_7dias'] = ventas_periodo(dias=7)
        ctx['productos_mas_pedidos'] = productos_mas_pedidos(limite=5)
        return ctx


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    """Ranking de repartidores."""
    template_name = 'reportes/repartidores.html'
    permission_required = 'pedidos.ver_reportes'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ranking'] = ranking_repartidores()
        return ctx