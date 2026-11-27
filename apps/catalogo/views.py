from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import OpcionProducto, Producto


class ProductoListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        queryset = Producto.objects.all()
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        queryset = Producto.objects.all()
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    form_class = AgregarAlCarritoForm
    permission_required = "pedidos.add_pedido"
    template_name = "catalogo/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        kwargs["producto"] = self.producto
        return kwargs

    def form_valid(self, form):
        cantidad = form.cleaned_data["cantidad"]
        campos = ("opcion_tamano", "opcion_leche", "opcion_azucar")
        ids = [
            form.cleaned_data[campo]
            for campo in campos
            if form.cleaned_data.get(campo)
        ]
        opciones = OpcionProducto.objects.filter(pk__in=ids)
        try:
            carrito = obtener_carrito(self.request.user)
            agregar_item(carrito, self.producto, cantidad, opciones)
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return super().form_valid(form)
