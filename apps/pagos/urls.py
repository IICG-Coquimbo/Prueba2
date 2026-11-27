from django.urls import path

from .views import PagoDetalleView, PagoFallidoView, PagoRealizadoView

app_name = "pagos"

urlpatterns = [
    path(
        "realizado/",
        PagoRealizadoView.as_view(),
        name="realizado",
    ),
    path(
        "fallido/",
        PagoFallidoView.as_view(),
        name="fallido",
    ),
    path(
        "detalle/<int:pk>/",
        PagoDetalleView.as_view(),
        name="detalle",
    ),
]