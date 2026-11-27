from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import DetailView, ListView, FormView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect, render

from pedidos.models import Pedido
from pedidos.servicios import (
    obtener_carrito,
    agregar_item,
    quitar_item,
    recalcular_totales,
    confirmar_pedido,
    aplicar_codigo,
)
from pedidos.forms import ConfirmarPedidoForm, CodigoForm, QuitarItemForm, AgregarAlCarritoForm
from catalogo.models import Producto
from cuentas.models import Direccion


class CarritoDetailView(PermissionRequiredMixin, DetailView):
    """Vista que muestra el carrito actual del usuario."""
    model = Pedido
    template_name = 'pedidos/carrito_detail.html'
    permission_required = 'pedidos.view_pedido'
    context_object_name = 'pedido'

    def get_queryset(self):
        # Solo muestra el pedido en estado carrito del usuario actual
        return Pedido.objects.filter(cliente=self.request.user, estado="carrito")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.cliente != self.request.user:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No tienes acceso a este carrito.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from pedidos.forms import CodigoForm, ConfirmarPedidoForm
        ctx['form_codigo'] = CodigoForm()
        ctx['form_direccion'] = ConfirmarPedidoForm()
        return ctx


class PedidoCreateView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    """Vista para confirmar el carrito y crear el pedido."""
    form_class = ConfirmarPedidoForm
    template_name = 'pedidos/pedido_form.html'
    permission_required = 'pedidos.add_pedido'
    success_url = reverse_lazy('pedidos:historial')
    success_message = "Pedido creado exitosamente."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        ctx['direcciones'] = Direccion.objects.filter(usuario=usuario)
        return ctx

    def form_valid(self, form):
        usuario = self.request.user
        carrito = obtener_carrito(usuario)
        # Validar que haya items
        if not carrito.items.exists():
            form.add_error(None, "El carrito está vacío.")
            return self.form_invalid(form)
        # Llamar al servicio que confirma el pedido (crea Pago y cambia estado)
        confirmar_pedido(carrito, form.cleaned_data["direccion"], form.cleaned_data["metodo_pago"])
        return super().form_valid(form)


class PedidoListView(PermissionRequiredMixin, ListView):
    """Historial de pedidos del usuario, filtrado por rol."""
    model = Pedido
    template_name = 'pedidos/pedido_list.html'
    permission_required = 'pedidos.view_pedido'
    context_object_name = 'pedidos'

    def get_queryset(self):
        usuario = self.request.user
        # Cliente: solo sus pedidos, excluidos carrito y pendiente_pago
        qs = Pedido.objects.filter(cliente=usuario).exclude(estado__in=["carrito", "pendiente_pago"])
        # Barista, Repartidor, Admin ver más; aquí dejamos la filtración básica.
        return qs.order_by("-creado")