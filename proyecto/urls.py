"""
URLs principales del proyecto Cafe Rincon.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from apps.inicio.views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("apps.cuentas.urls", namespace="cuentas")),
    path("catalogo/", include("apps.catalogo.urls", namespace="catalogo")),
    path("promociones/", include("apps.promociones.urls", namespace="promociones")),
    path("pedidos/", include("apps.pedidos.urls", namespace="pedidos")),
    path("pagos/", include("apps.pagos.urls", namespace="pagos")),
    path("entregas/", include("apps.entregas.urls", namespace="entregas")),
    path("reportes/", include("apps.reportes.urls", namespace="reportes")),
    re_path(r"^$", HomeView.as_view(), name="inicio"),
]