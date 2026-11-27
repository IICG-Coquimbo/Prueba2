from django.views.generic import ListView, DetailView, FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect

from .models import Producto
from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import obtener_carrito, agregar_item


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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = AgregarAlCarritoForm(producto=self.object)
        return ctx


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_detail.html"
    success_url = reverse_lazy("catalogo:producto_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        producto = self.get_form_kwargs()["producto"]
        usuario = self.request.user
        pedido = obtener_carrito(usuario)
        cantidad = form.cleaned_data["cantidad"]
        opciones = []
        for campo, valor in form.cleaned_data.items():
            if campo.startswith("opcion_") and valor is not None:
                opciones.append(valor)
        try:
            agregar_item(pedido, producto, cantidad, opciones)
        except Exception as exc:
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "No se pudo agregar el producto al carrito.")
        return redirect("catalogo:producto_detail", pk=self.kwargs["pk"])
