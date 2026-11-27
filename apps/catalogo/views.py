from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from .models import Producto
from apps.pedidos.forms import AgregarAlCarritoForm


class ProductoListView(ListView):
    model = Producto
    template_name = 'catalogo/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.has_perm('catalogo.change_producto'):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'catalogo/producto_detail.html'
    context_object_name = 'producto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AgregarAlCarritoForm(producto=self.object)
        return context


# Placeholder para la vista que creará @flujo/@vistas
class AgregarAlCarritoView(PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = 'catalogo/producto_detail.html'
    context_object_name = 'producto'
    permission_required = 'pedidos.add_pedido'