from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.servicios import agregar_item, obtener_carrito

from .forms import AgregarAlCarritoForm
from .models import OpcionProducto, Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"
    raise_exception = True
    template_name = "catalogo/producto_list.html"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset.order_by("categoria__nombre", "nombre")


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"
    raise_exception = True
    template_name = "catalogo/producto_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    success_url = reverse_lazy("catalogo:producto_list")
    success_message = "Producto agregado al carrito."

    def get_producto(self):
        if not hasattr(self, "producto"):
            self.producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return self.producto

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.get_producto()
        return kwargs

    def form_valid(self, form):
        producto = self.get_producto()
        opciones = [
            form.cleaned_data.get(tipo)
            for tipo in OpcionProducto.TipoOpcion.values
        ]
        try:
            agregar_item(
                obtener_carrito(self.request.user),
                producto,
                form.cleaned_data["cantidad"],
                opciones,
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        return super().form_valid(form)
