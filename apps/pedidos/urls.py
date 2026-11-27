from django.urls import path

from .views import (
    PedidoCarritoCodigoView,
    PedidoCarritoConfirmarView,
    PedidoCarritoDetailView,
    PedidoDetailView,
    PedidoEstadoView,
    PedidoItemQuitarView,
    PedidoListView,
)

app_name = "pedidos"

urlpatterns = [
    path("carrito/", PedidoCarritoDetailView.as_view(), name="carrito_detail"),
    path("carrito/quitar/<int:pk>/", PedidoItemQuitarView.as_view(), name="item_quitar"),
    path("carrito/codigo/", PedidoCarritoCodigoView.as_view(), name="carrito_codigo"),
    path("carrito/confirmar/", PedidoCarritoConfirmarView.as_view(), name="carrito_confirmar"),
    path("pedidos/", PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/<int:pk>/", PedidoDetailView.as_view(), name="pedido_detail"),
    path("pedidos/<int:pk>/estado/", PedidoEstadoView.as_view(), name="pedido_estado"),
]
