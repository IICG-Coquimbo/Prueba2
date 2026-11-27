from django.urls import path

from .views import (
    CarritoDetailView, ItemQuitarView, CarritoCodigoView,
    CarritoConfirmarView, PedidoListView, PedidoDetailView, PedidoEstadoView,
)

app_name = "pedidos"

urlpatterns = [
    path("carrito/", CarritoDetailView.as_view(), name="carrito_detail"),
    path("carrito/quitar/<int:pk>/", ItemQuitarView.as_view(), name="item_quitar"),
    path("carrito/codigo/", CarritoCodigoView.as_view(), name="carrito_codigo"),
    path("carrito/confirmar/", CarritoConfirmarView.as_view(), name="carrito_confirmar"),
    path("", PedidoListView.as_view(), name="pedido_list"),
    path("<int:pk>/", PedidoDetailView.as_view(), name="pedido_detail"),
    path("<int:pk>/estado/", PedidoEstadoView.as_view(), name="pedido_estado"),
]
