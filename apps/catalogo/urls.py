from django.urls import re_path

from apps.catalogo import views

app_name = "catalogo"

urlpatterns = [
    re_path(r"^menu/$", views.ProductoListView.as_view(), name="producto_list"),
    re_path(r"^menu/(?P<pk>\d+)/$", views.ProductoDetailView.as_view(), name="producto_detail"),
    re_path(r"^menu/(?P<pk>\d+)/agregar/$", views.ProductoAgregarView.as_view(), name="producto_agregar"),
]
