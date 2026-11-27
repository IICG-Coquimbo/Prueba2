from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

from catalogo.models import Categoria, Producto


class CategoriaListView(PermissionRequiredMixin, ListView):
    """Listado de categorias."""
    model = Categoria
    template_name = 'catalogo/categoria_list.html'
    permission_required = 'catalogo.view_categoria'
    context_object_name = 'categorias'


class ProductoListView(PermissionRequiredMixin, ListView):
    """Listado de productos disponibles."""
    model = Producto
    template_name = 'catalogo/producto_list.html'
    permission_required = 'catalogo.view_producto'
    context_object_name = 'productos'


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    """Detalle de un producto."""
    model = Producto
    template_name = 'catalogo/producto_detail.html'
    permission_required = 'catalogo.view_producto'
    context_object_name = 'producto'
