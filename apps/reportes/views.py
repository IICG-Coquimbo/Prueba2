from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from apps.pedidos.servicios import (
    ventas_periodo, productos_mas_pedidos, ranking_repartidores,
)


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_panel.html"
    permission_required = "pedidos.ver_reportes"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ventas_hoy"] = ventas_periodo(1)
        ctx["ventas_semana"] = ventas_periodo(7)
        ctx["productos_top"] = productos_mas_pedidos(limite=5)
        return ctx


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_repartidores.html"
    permission_required = "pedidos.ver_reportes"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["repartidores"] = ranking_repartidores()
        return ctx
