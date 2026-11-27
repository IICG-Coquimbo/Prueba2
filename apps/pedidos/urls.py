from django.urls import path

from .views import (
    ItemPedidoQuitarView,
    PedidoCarritoView,
    PedidoCodigoView,
    PedidoConfirmarView,
    PedidoDetailView,
    PedidoEstadoView,
    PedidoListView,
)

app_name = "pedidos"

urlpatterns = [
    path("carrito/", PedidoCarritoView.as_view(), name="carrito_detail"),
    path(
        "carrito/quitar/<int:pk>/",
        ItemPedidoQuitarView.as_view(),
        name="item_quitar",
    ),
    path("carrito/codigo/", PedidoCodigoView.as_view(), name="carrito_codigo"),
    path(
        "carrito/confirmar/",
        PedidoConfirmarView.as_view(),
        name="carrito_confirmar",
    ),
    path("pedidos/", PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/<int:pk>/", PedidoDetailView.as_view(), name="pedido_detail"),
    path(
        "pedidos/<int:pk>/estado/",
        PedidoEstadoView.as_view(),
        name="pedido_estado",
    ),
]
