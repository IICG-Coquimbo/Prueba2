from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import OpcionProducto, Producto
from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"

    def get_queryset(self):
        qs = Producto.objects.all()
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"
    success_url = reverse_lazy("catalogo:producto_list")

    def get_object(self):
        return get_object_or_404(Producto, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["producto"] = self.get_object()
        return context

    def form_valid(self, form):
        producto = self.get_object()
        carrito = obtener_carrito(self.request.user)
        opciones = []
        for nombre_campo, valor in form.cleaned_data.items():
            if nombre_campo.startswith("opcion_") and valor:
                try:
                    opcion = OpcionProducto.objects.get(id=int(valor))
                    if opcion.producto_id == producto.id:
                        opciones.append(opcion)
                except (ValueError, OpcionProducto.DoesNotExist):
                    pass
        try:
            agregar_item(carrito, producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return super().form_valid(form)
