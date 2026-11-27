from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView, ListView

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/producto_list.html"
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").order_by("nombre")
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/producto_detail.html"
    permission_required = "catalogo.view_producto"
