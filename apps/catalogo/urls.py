from django.urls import path

from catalogo.views import CategoriaListView, ProductoListView, ProductoDetailView

app_name = 'catalogo'

urlpatterns = [
    path('categorias/', CategoriaListView.as_view(), name='categoria_list'),
    path('productos/', ProductoListView.as_view(), name='producto_list'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto_detail'),
]