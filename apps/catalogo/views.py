from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import OpcionProducto, Producto
from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").order_by("categoria__nombre", "nombre")
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").prefetch_related(
            Prefetch("opciones", queryset=OpcionProducto.objects.order_by("tipo", "nombre"))
        )
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_agregar"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"], disponible=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Agregar {self.producto.nombre} al carrito"
        context["boton"] = "Agregar al carrito"
        context["cancelar_url"] = reverse_lazy("catalogo:producto_detail", kwargs={"pk": self.producto.pk})
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            agregar_item(
                carrito,
                self.producto,
                form.cleaned_data["cantidad"],
                form.get_opciones(),
            )
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return redirect("pedidos:carrito_detail")
