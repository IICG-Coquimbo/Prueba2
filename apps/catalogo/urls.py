from django.urls import path

from .views import ProductoAgregarView, ProductoDetailView, ProductoListView

app_name = "catalogo"

urlpatterns = [
    path("productos/", ProductoListView.as_view(), name="producto_list"),
    path("productos/<int:pk>/", ProductoDetailView.as_view(), name="producto_detail"),
    path(
        "productos/<int:pk>/agregar/",
        ProductoAgregarView.as_view(),
        name="producto_agregar",
    ),
]
