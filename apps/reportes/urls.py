from django.urls import path

from apps.reportes import views

app_name = "reportes"

urlpatterns = [
    path("", views.ReportePanelView.as_view(), name="reporte_panel"),
    path("repartidores/", views.ReporteRepartidoresView.as_view(), name="reporte_repartidores"),
]
