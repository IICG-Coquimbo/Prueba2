from django.urls import path

from .views import ProductoDetailView, ProductoListView

app_name = "catalogo"

urlpatterns = [
    path("menu/", ProductoListView.as_view(), name="producto_list"),
    path("menu/<int:pk>/", ProductoDetailView.as_view(), name="producto_detail"),
]
