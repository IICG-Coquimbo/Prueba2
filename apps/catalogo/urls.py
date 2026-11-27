from django.urls import path

from apps.catalogo.views import ProductoAgregarView, ProductoDetailView, ProductoListView

app_name = "catalogo"

urlpatterns = [
    path("menu/", ProductoListView.as_view(), name="producto_list"),
    path("menu/<int:pk>/", ProductoDetailView.as_view(), name="producto_detail"),
    path("menu/<int:pk>/agregar/", ProductoAgregarView.as_view(), name="producto_agregar"),
]
