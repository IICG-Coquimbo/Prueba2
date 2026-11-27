from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import OpcionProducto, Producto
from apps.pedidos.forms import AgregarAlCarritoForm


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"

    def get_queryset(self):
        queryset = Producto.objects.all()
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["form"] = AgregarAlCarritoForm(producto=self.object)
        return contexto


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_agregar_form.html"

    def get_producto(self):
        return get_object_or_404(Producto, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.get_producto()
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["producto"] = self.get_producto()
        return contexto

    def form_valid(self, form):
        from apps.pedidos.servicios import agregar_item, obtener_carrito

        producto = self.get_producto()
        carrito = obtener_carrito(self.request.user)
        opciones = []
        for tipo in ["tamano", "leche", "azucar"]:
            valor = form.cleaned_data.get("opcion_{}".format(tipo))
            if valor:
                try:
                    opciones.append(OpcionProducto.objects.get(pk=int(valor), producto=producto))
                except (OpcionProducto.DoesNotExist, ValueError, TypeError):
                    pass
        try:
            agregar_item(carrito, producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as error:
            form.add_error(None, error.message)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito")
