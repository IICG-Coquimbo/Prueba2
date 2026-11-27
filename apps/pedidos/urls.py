from django.urls import path

from .views import (
    CarritoCodigoView,
    CarritoConfirmarView,
    CarritoDetailView,
    ItemQuitarView,
    PedidoDetailView,
    PedidoEstadoView,
    PedidoListView,
)

app_name = "pedidos"

urlpatterns = [
    path("carrito/", CarritoDetailView.as_view(), name="carrito_detail"),
    path("carrito/quitar/<int:pk>/", ItemQuitarView.as_view(), name="item_quitar"),
    path("carrito/codigo/", CarritoCodigoView.as_view(), name="carrito_codigo"),
    path("carrito/confirmar/", CarritoConfirmarView.as_view(), name="carrito_confirmar"),
    path("pedidos/", PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/<int:pk>/", PedidoDetailView.as_view(), name="pedido_detail"),
    path("pedidos/<int:pk>/estado/", PedidoEstadoView.as_view(), name="pedido_estado"),
]
