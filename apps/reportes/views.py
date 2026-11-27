from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from apps.pedidos.servicios import (
    productos_mas_pedidos,
    ranking_repartidores,
    ventas_periodo,
)


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_panel.html"
    permission_required = "pedidos.ver_reportes"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ventas_hoy"] = ventas_periodo(1)
        context["ventas_7_dias"] = ventas_periodo(7)
        context["productos"] = productos_mas_pedidos()
        return context


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_repartidores.html"
    permission_required = "pedidos.ver_reportes"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["repartidores"] = ranking_repartidores()
        return context
