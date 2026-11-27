from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views.generic import DetailView, ListView

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"

    def get_queryset(self):
        qs = Producto.objects.all()
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"
