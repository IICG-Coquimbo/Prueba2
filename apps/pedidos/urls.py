from django.urls import re_path

from . import views


app_name = "pedidos"

urlpatterns = [
    re_path(r"^carrito/$", views.CarritoDetailView.as_view(), name="carrito_detail"),
    re_path(r"^carrito/quitar/(?P<pk>[0-9]+)/$", views.ItemQuitarView.as_view(), name="item_quitar"),
    re_path(r"^carrito/codigo/$", views.CarritoCodigoView.as_view(), name="carrito_codigo"),
    re_path(r"^carrito/confirmar/$", views.CarritoConfirmarView.as_view(), name="carrito_confirmar"),
    re_path(r"^menu/(?P<pk>[0-9]+)/agregar/$", views.ProductoAgregarView.as_view(), name="producto_agregar"),
    re_path(r"^pedidos/$", views.PedidoListView.as_view(), name="pedido_list"),
    re_path(r"^pedidos/(?P<pk>[0-9]+)/$", views.PedidoDetailView.as_view(), name="pedido_detail"),
]
