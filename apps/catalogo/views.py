from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.catalogo.models import Producto, Categoria
from apps.catalogo.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import obtener_carrito, agregar_item


class ProductoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"
    paginate_by = 12
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        qs = super().get_queryset().select_related("categoria")
        if not self.request.user.has_perm("catalogo.change_producto"):
            qs = qs.filter(disponible=True)
        return qs


class ProductoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Producto
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = AgregarAlCarritoForm(producto=self.object)
        return context


class AgregarAlCarritoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = AgregarAlCarritoForm
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        kwargs["producto"] = producto
        return kwargs

    def form_valid(self, form):
        producto = get_object_or_404(Producto, pk=self.kwargs["pk"])
        carrito = obtener_carrito(self.request.user)
        opciones_ids = []
        for key, value in form.cleaned_data.items():
            if key.startswith("opcion_") and value:
                opciones_ids.append(int(value))
        try:
            agregar_item(carrito, producto, form.cleaned_data["cantidad"], opciones_ids)
            messages.success(self.request, f"{producto.nombre} agregado al carrito.")
        except Exception as e:
            messages.error(self.request, str(e))
        return redirect("catalogo:producto_list")