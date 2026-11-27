from django.urls import path
from .views import ProductoListView, ProductoDetailView, AgregarAlCarritoView

app_name = 'catalogo'
urlpatterns = [
    path('', ProductoListView.as_view(), name='producto_list'),
    path('<int:pk>/', ProductoDetailView.as_view(), name='producto_detail'),
    path('<int:pk>/agregar/', AgregarAlCarritoView.as_view(), name='producto_agregar'),
]