from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.servicios import agregar_item, obtener_carrito

from .forms import AgregarAlCarritoForm
from .models import Producto


class ProductoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "object_list"
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria").all()
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/producto_detail.html"
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = AgregarAlCarritoForm(producto=self.object)
        return ctx


class ProductoAgregarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["producto"] = self.producto
        ctx["object"] = self.producto
        return ctx

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            agregar_item(
                carrito,
                self.producto,
                form.cleaned_data["cantidad"],
                form.opciones_elegidas(),
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        return redirect(reverse_lazy("pedidos:carrito_detail"))
