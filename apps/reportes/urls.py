from django.urls import path

from reportes.views import ReportePanelView, ReporteRepartidoresView

app_name = 'reportes'

urlpatterns = [
    path('', ReportePanelView.as_view(), name='panel'),
    path('repartidores/', ReporteRepartidoresView.as_view(), name='repartidores'),
]