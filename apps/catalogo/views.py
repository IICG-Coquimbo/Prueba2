from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"
    template_name = "catalogo/producto_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context
