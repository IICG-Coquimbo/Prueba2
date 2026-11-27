from django.contrib import admin
from django.urls import include, re_path

from apps.inicio.views import HomeView

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^$", HomeView.as_view(), name="inicio"),
    re_path(r"^", include("apps.catalogo.urls")),
    re_path(r"^", include("apps.pedidos.urls")),
    re_path(r"^", include("apps.pagos.urls")),
    re_path(r"^", include("apps.entregas.urls")),
    re_path(r"^", include("apps.reportes.urls")),
    re_path(r"^", include("apps.cuentas.urls")),
]
