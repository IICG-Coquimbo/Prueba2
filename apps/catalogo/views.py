from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Categoria, Producto, OpcionProducto
from .forms import CategoriaForm, ProductoForm, OpcionProductoForm
from apps.pedidos.forms import AgregarAlCarritoForm


class CategoriaListView(PermissionRequiredMixin, ListView):
    model = Categoria
    template_name = "catalogo/categoria_list.html"
    context_object_name = "object_list"
    permission_required = "catalogo.view_categoria"


class CategoriaDetailView(PermissionRequiredMixin, DetailView):
    model = Categoria
    template_name = "catalogo/categoria_detail.html"
    permission_required = "catalogo.view_categoria"


class CategoriaCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categoria_list")
    success_message = "Categoria creada correctamente."
    permission_required = "catalogo.add_categoria"


class CategoriaUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"
    success_url = reverse_lazy("catalogo:categoria_list")
    success_message = "Categoria actualizada correctamente."
    permission_required = "catalogo.change_categoria"


class CategoriaDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Categoria
    template_name = "catalogo/categoria_confirm_delete.html"
    success_url = reverse_lazy("catalogo:categoria_list")
    success_message = "Categoria eliminada correctamente."
    permission_required = "catalogo.delete_categoria"


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "object_list"
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/producto_detail.html"
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["agregar_form"] = AgregarAlCarritoForm(producto=self.object)
        return ctx


class ProductoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/producto_form.html"
    success_url = reverse_lazy("catalogo:producto_list")
    success_message = "Producto creado correctamente."
    permission_required = "catalogo.add_producto"


class ProductoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/producto_form.html"
    success_url = reverse_lazy("catalogo:producto_list")
    success_message = "Producto actualizado correctamente."
    permission_required = "catalogo.change_producto"


class ProductoDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Producto
    template_name = "catalogo/producto_confirm_delete.html"
    success_url = reverse_lazy("catalogo:producto_list")
    success_message = "Producto eliminado correctamente."
    permission_required = "catalogo.delete_producto"


class OpcionProductoListView(PermissionRequiredMixin, ListView):
    model = OpcionProducto
    template_name = "catalogo/opcionproducto_list.html"
    context_object_name = "object_list"
    permission_required = "catalogo.view_opcionproducto"


class OpcionProductoDetailView(PermissionRequiredMixin, DetailView):
    model = OpcionProducto
    template_name = "catalogo/opcionproducto_detail.html"
    permission_required = "catalogo.view_opcionproducto"


class OpcionProductoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = OpcionProducto
    form_class = OpcionProductoForm
    template_name = "catalogo/opcionproducto_form.html"
    success_url = reverse_lazy("catalogo:opcionproducto_list")
    success_message = "Opcion creada correctamente."
    permission_required = "catalogo.add_opcionproducto"


class OpcionProductoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = OpcionProducto
    form_class = OpcionProductoForm
    template_name = "catalogo/opcionproducto_form.html"
    success_url = reverse_lazy("catalogo:opcionproducto_list")
    success_message = "Opcion actualizada correctamente."
    permission_required = "catalogo.change_opcionproducto"


class OpcionProductoDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = OpcionProducto
    template_name = "catalogo/opcionproducto_confirm_delete.html"
    success_url = reverse_lazy("catalogo:opcionproducto_list")
    success_message = "Opcion eliminada correctamente."
    permission_required = "catalogo.delete_opcionproducto"
