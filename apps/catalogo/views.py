from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import OpcionProducto, Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto

    def get_queryset(self):
        productos = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            productos = productos.filter(disponible=True)
        return productos.order_by("categoria__nombre", "nombre", "pk")


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto

    def get_queryset(self):
        productos = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            productos = productos.filter(disponible=True)
        return productos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        if self.object.disponible and self.request.user.has_perm("pedidos.add_pedido"):
            contexto["form"] = AgregarAlCarritoForm(
                producto=self.object, usuario=self.request.user
            )
        return contexto


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_agregar_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")
    carrito = None

    @cached_property
    def producto(self):
        return get_object_or_404(Producto, pk=self.kwargs["pk"], disponible=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(producto=self.producto, pedido=self.carrito, usuario=self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(producto=self.producto, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # El formulario requiere un carrito persistido para validar el POST.
        try:
            self.carrito = obtener_carrito(request.user)
        except ValidationError as error:
            form = self.get_form()
            form.add_error(None, error)
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        opciones = [form.cleaned_data[tipo] for tipo in OpcionProducto.Tipo.values]
        try:
            agregar_item(self.carrito, self.producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        response = super().form_valid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return response

    def form_invalid(self, form):
        if self.carrito is not None:
            # Un envío inválido no debe dejar un carrito vacío recién creado.
            transaction.set_rollback(True)
        return super().form_invalid(form)
