from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.forms import AgregarAlCarritoForm
from apps.catalogo.models import Producto
from apps.pedidos.servicios import agregar_item, obtener_carrito


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").prefetch_related("opciones")
        if not self.request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        queryset = Producto.objects.all()
        if not request.user.has_perm("catalogo.change_producto"):
            queryset = queryset.filter(disponible=True)
        self.producto = get_object_or_404(queryset, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Agregar al carrito"
        return context

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            agregar_item(
                pedido,
                self.producto,
                form.cleaned_data["cantidad"],
                form.opciones_seleccionadas(),
            )
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return redirect("pedidos:carrito_detail")
