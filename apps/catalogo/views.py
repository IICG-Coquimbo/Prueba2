from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import Producto, TipoOpcion
from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").all()
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = get_object_or_404(Producto, pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        opciones = [form.cleaned_data[t] for t in TipoOpcion.values if form.cleaned_data.get(t)]
        try:
            agregar_item(carrito, form.producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as e:
            form.add_error(None, "; ".join(e.messages))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return redirect("pedidos:carrito_detail")
