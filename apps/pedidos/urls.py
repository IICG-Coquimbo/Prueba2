from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    # Acciones del flujo
    path("menu/<int:pk>/agregar/", views.ProductoAgregarView.as_view(), name="producto_agregar"),
    path("carrito/", views.CarritoDetailView.as_view(), name="carrito_detail"),
    path("carrito/quitar/<int:pk>/", views.ItemQuitarView.as_view(), name="item_quitar"),
    path("carrito/codigo/", views.CarritoCodigoView.as_view(), name="carrito_codigo"),
    path("carrito/confirmar/", views.CarritoConfirmarView.as_view(), name="carrito_confirmar"),
    path("pasarela/<str:referencia>/", views.PasarelaView.as_view(), name="pasarela"),
    # Pedidos
    path("pedidos/", views.PedidoListView.as_view(), name="pedido_list"),
    path("pedidos/<int:pk>/", views.PedidoDetailView.as_view(), name="pedido_detail"),
    path("pedidos/<int:pk>/estado/", views.PedidoEstadoView.as_view(), name="pedido_estado"),
    # CRUD estándar
    path("pedidos/nuevo/", views.PedidoCreateView.as_view(), name="pedido_create"),
    path("pedidos/<int:pk>/editar/", views.PedidoUpdateView.as_view(), name="pedido_update"),
    path("pedidos/<int:pk>/borrar/", views.PedidoDeleteView.as_view(), name="pedido_delete"),
    path("items/nuevo/", views.ItemPedidoCreateView.as_view(), name="itempedido_create"),
    path("items/<int:pk>/editar/", views.ItemPedidoUpdateView.as_view(), name="itempedido_update"),
    path("items/<int:pk>/borrar/", views.ItemPedidoDeleteView.as_view(), name="itempedido_delete"),
    path("historial/", views.HistorialEstadoListView.as_view(), name="historialestado_list"),
]
