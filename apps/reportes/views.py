from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin

from apps.pedidos.servicios import ventas_periodo, productos_mas_pedidos, ranking_repartidores


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/reporte_panel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ventas_hoy"] = ventas_periodo(1)
        ctx["ventas_semana"] = ventas_periodo(7)
        ctx["productos_top"] = productos_mas_pedidos(limite=5)
        return ctx


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/reporte_repartidores.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ranking"] = ranking_repartidores()
        return ctx
