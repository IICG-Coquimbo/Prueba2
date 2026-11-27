from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import Producto
from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito


class ProductoListView(PermissionRequiredMixin, ListView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").all()
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    model = Producto
    permission_required = "catalogo.view_producto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_agregar"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_message = "Producto agregado al carrito."

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Agregar {self.producto.nombre}"
        context["boton_texto"] = "Agregar al carrito"
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        opciones = []
        for tipo in ("tamano", "leche", "azucar"):
            opcion_id = form.cleaned_data.get(tipo)
            if opcion_id:
                opcion = self.producto.opciones.filter(pk=opcion_id, tipo=tipo).first()
                if opcion:
                    opciones.append(opcion)
        try:
            agregar_item(carrito, self.producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as exc:
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:carrito_detail")
