from django.urls import path

from pedidos.views import CarritoDetailView, PedidoCreateView, PedidoListView

app_name = 'pedidos'

urlpatterns = [
    path('carrito/', CarritoDetailView.as_view(), name='carrito_detail'),
    path('carrito/confirmar/', PedidoCreateView.as_view(), name='pedido_confirmar'),
    path('historial/', PedidoListView.as_view(), name='historial'),
]