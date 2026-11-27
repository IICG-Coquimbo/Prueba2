from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView
from apps.pedidos.servicios import ventas_periodo, productos_mas_pedidos, ranking_repartidores


class ReportePanelView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_panel.html"
    permission_required = "pedidos.ver_reportes"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ventas_hoy"] = ventas_periodo(1)
        context["ventas_semana"] = ventas_periodo(7)
        context["productos_top"] = productos_mas_pedidos(5)
        return context


class ReporteRepartidoresView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "reportes/reporte_repartidores.html"
    permission_required = "pedidos.ver_reportes"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ranking"] = ranking_repartidores()
        return context