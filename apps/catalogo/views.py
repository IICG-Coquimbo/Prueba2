from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import Producto
from .forms import AgregarAlCarritoForm


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
        context["form"] = AgregarAlCarritoForm(self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_agregar.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        carrito = obtener_carrito(self.request.user)
        try:
            opciones = []
            for campo, valor in form.cleaned_data.items():
                if campo.startswith("opcion_") and valor:
                    opciones.append(valor)
            agregar_item(
                carrito,
                producto,
                form.cleaned_data["cantidad"],
                opciones,
            )
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")
