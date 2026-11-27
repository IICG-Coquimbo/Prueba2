from django.urls import path

from . import views


app_name = "pedidos"

urlpatterns = [
    path("carrito/", views.CarritoDetailView.as_view(), name="carrito_detail"),
    path("carrito/quitar/<int:pk>/", views.ItemQuitarView.as_view(), name="item_quitar"),
    path("carrito/codigo/", views.CarritoCodigoView.as_view(), name="carrito_codigo"),
    path("carrito/confirmar/", views.CarritoConfirmarView.as_view(), name="carrito_confirmar"),
    path("pedidos/", views.PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detail"),
    path("pedidos/<int:pk>/estado/", views.PedidoEstadoView.as_view(), name="pedido_estado"),
]
