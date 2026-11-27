from django.urls import path
from apps.catalogo import views

app_name = "catalogo"

urlpatterns = [
    path("", views.ProductoListView.as_view(), name="producto_list"),
    path("<int:pk>/", views.ProductoDetailView.as_view(), name="producto_detail"),
    path("<int:pk>/agregar/", views.AgregarAlCarritoView.as_view(), name="producto_agregar"),
]