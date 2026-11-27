from django.urls import path
from apps.pedidos import views

app_name = "pedidos"

urlpatterns = [
    # path("", views.PedidoListView.as_view(), name="pedido_list"),
    # path("<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detail"),
    # path("<int:pk>/estado/", views.PedidoEstadoView.as_view(), name="pedido_estado"),
    # path("carrito/", views.CarritoDetailView.as_view(), name="carrito_detail"),
    # path("carrito/quitar/<int:pk>/", views.ItemQuitarView.as_view(), name="item_quitar"),
    # path("carrito/codigo/", views.CarritoCodigoView.as_view(), name="carrito_codigo"),
    # path("carrito/confirmar/", views.CarritoConfirmarView.as_view(), name="carrito_confirmar"),
]