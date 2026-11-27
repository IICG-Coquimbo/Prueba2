from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from apps.pedidos.servicios import (
    productos_mas_pedidos,
    ranking_repartidores,
    ventas_periodo,
)


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/reporte_panel.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["ventas_hoy"] = ventas_periodo(1)
        contexto["ventas_7_dias"] = ventas_periodo(7)
        contexto["productos"] = productos_mas_pedidos()
        return contexto


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/reporte_repartidores.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["ranking"] = ranking_repartidores()
        return contexto
