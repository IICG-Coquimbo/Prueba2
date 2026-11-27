from django.urls import path
from . import views

app_name = "reportes"

urlpatterns = [
    path("reportes/", views.ReportePanelView.as_view(), name="reporte_panel"),
    path("reportes/repartidores/", views.ReporteRepartidoresView.as_view(), name="reporte_repartidores"),
]
