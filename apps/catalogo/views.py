"""Vistas de la app catalogo segun docs/reglas_vistas_templates.md."""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        qs = Producto.objects.all()
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    """Vista para agregar un producto al carrito (FormView de la accion del flujo)."""

    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_detail.html"
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        kwargs["producto"] = self.producto
        return kwargs

    def form_valid(self, form):
        from apps.pedidos.servicios import agregar_item, obtener_carrito

        cantidad = form.cleaned_data["cantidad"]
        opciones = []
        for tipo in ("tamano", "leche", "azucar"):
            campo = f"opcion_{tipo}"
            if campo in form.cleaned_data and form.cleaned_data[campo]:
                opciones.append(form.cleaned_data[campo])
        pedido = obtener_carrito(self.request.user)
        try:
            agregar_item(pedido, self.producto, cantidad, opciones)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["producto"] = self.producto
        return context
