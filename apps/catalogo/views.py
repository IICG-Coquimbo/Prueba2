from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    ordering = ["categoria__nombre", "nombre"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto

    def get_queryset(self):
        queryset = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["producto"] = self.producto
        return context

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        opciones = [
            cleaned_data[tipo]
            for tipo in ("tamano", "leche", "azucar")
            if cleaned_data.get(tipo) is not None
        ]
        carrito = obtener_carrito(self.request.user)
        try:
            agregar_item(carrito, self.producto, cleaned_data["cantidad"], opciones)
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return super().form_valid(form)
