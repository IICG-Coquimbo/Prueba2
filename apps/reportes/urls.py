from django.urls import path

from .views import ReportePanelView, ReporteRepartidoresView

app_name = "reportes"

urlpatterns = [
    path("", ReportePanelView.as_view(), name="reporte_panel"),
    path("repartidores/", ReporteRepartidoresView.as_view(), name="reporte_repartidores"),
]
