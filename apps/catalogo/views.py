from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").order_by(
            "categoria__nombre", "nombre", "pk"
        )
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    template_name = "catalogo/accion_form.html"
    form_class = AgregarAlCarritoForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
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
        pedido = obtener_carrito(self.request.user)
        try:
            agregar_item(
                pedido,
                self.producto,
                form.cleaned_data["cantidad"],
                form.cleaned_data["opciones"],
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")
