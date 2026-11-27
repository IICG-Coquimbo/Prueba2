from django.urls import re_path

from apps.pedidos import views

app_name = "pedidos"

urlpatterns = [
    re_path(r"^carrito/$", views.carrito_detail, name="carrito"),
    re_path(r"^carrito/item/(?P<pk>\d+)/quitar/$", views.item_quitar, name="item_quitar"),
    re_path(r"^carrito/codigo/$", views.carrito_codigo, name="carrito_codigo"),
    re_path(r"^carrito/confirmar/$", views.carrito_confirmar, name="carrito_confirmar"),
    re_path(r"^$", views.pedido_list, name="pedido_list"),
    re_path(r"^(?P<pk>\d+)/$", views.pedido_detail, name="pedido_detail"),
    re_path(r"^(?P<pk>\d+)/estado/$", views.pedido_estado, name="pedido_estado"),
]
