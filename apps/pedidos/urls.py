from django.urls import path
from .views import (
    CarritoDetailView,
    AgregarAlCarritoView,
    QuitarItemView,
    AplicarCodigoView,
    ConfirmarPedidoView,
    PedidoListView,
    PedidoDetailView,
    AvanzarEstadoView,
)

app_name = 'pedidos'
urlpatterns = [
    path('carrito/', CarritoDetailView.as_view(), name='carrito_detail'),
    path('carrito/agregar/<int:producto_id>/', AgregarAlCarritoView.as_view(), name='producto_agregar'),
    path('carrito/quitar/<int:item_id>/', QuitarItemView.as_view(), name='item_quitar'),
    path('carrito/codigo/', AplicarCodigoView.as_view(), name='carrito_codigo'),
    path('carrito/confirmar/', ConfirmarPedidoView.as_view(), name='carrito_confirmar'),
    path('', PedidoListView.as_view(), name='pedido_list'),
    path('<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
    path('<int:pk>/estado/', AvanzarEstadoView.as_view(), name='pedido_estado'),
]