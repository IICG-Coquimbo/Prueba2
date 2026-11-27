from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("menu/", views.ProductoListView.as_view(), name="producto_list"),
    path("menu/<int:pk>/", views.ProductoDetailView.as_view(), name="producto_detail"),
]
