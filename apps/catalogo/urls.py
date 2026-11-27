from django.urls import re_path

from . import views


app_name = "catalogo"

urlpatterns = [
    re_path(r"^menu/$", views.ProductoListView.as_view(), name="producto_list"),
    re_path(r"^menu/(?P<pk>[0-9]+)/$", views.ProductoDetailView.as_view(), name="producto_detail"),
]
