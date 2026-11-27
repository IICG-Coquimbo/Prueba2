from django.views.generic import ListView, DetailView, FormView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q

from .models import Pedido, ItemPedido
from apps.cuentas.models import Direccion
from .forms import QuitarItemForm, CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm
from .servicios import (
    obtener_carrito, quitar_item, aplicar_codigo, confirmar_pedido,
    avanzar_pedido, registrar_estado,
)


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.add_pedido"
    template_name = "pedidos/carrito_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        ctx["pedido"] = pedido
        ctx["items"] = pedido.items.all()
        ctx["form_codigo"] = CodigoForm()
        ctx["form_confirmar"] = ConfirmarPedidoForm(usuario=self.request.user)
        return ctx


class ItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm

    def post(self, request, pk):
        item = get_object_or_404(ItemPedido, pk=pk)
        if item.pedido.cliente_id != request.user.id:
            messages.error(request, "No puedes quitar items de este carrito.")
            return redirect("pedidos:carrito_detail")
        try:
            quitar_item(item)
            messages.success(request, "Item eliminado del carrito.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data["codigo"])
            messages.success(self.request, "Codigo de descuento aplicado.")
        except Exception as exc:
            messages.error(self.request, str(exc))
        return redirect("pedidos:carrito_detail")

    def form_invalid(self, form):
        messages.error(self.request, "Codigo invalido.")
        return redirect("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = ConfirmarPedidoForm

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        direccion = form.cleaned_data["direccion"]
        metodo_pago = form.cleaned_data["metodo_pago"]
        try:
            pago = confirmar_pedido(pedido, direccion, metodo_pago)
            if metodo_pago == Pedido.METODO_EFECTIVO:
                messages.success(self.request, "Pedido confirmado con pago en efectivo.")
                return redirect("pedidos:pedido_detail", pk=pedido.pk)
            else:
                messages.success(self.request, "Pedido pendiente de pago. Pasa a la pasarela.")
                return redirect("pagos:pasarela", referencia=pago.referencia)
        except Exception as exc:
            messages.error(self.request, str(exc))
            return self.form_invalid(form)

    def form_invalid(self, form):
        return redirect("pedidos:carrito_detail")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.exclude(estado=Pedido.ESTADO_CARRITO)
        if user.has_perm("pedidos.despachar_pedido") or user.is_staff:
            return qs.exclude(estado=Pedido.ESTADO_CARRITO).order_by("creado")
        if user.has_perm("pedidos.preparar_pedido"):
            estados = [
                Pedido.ESTADO_RECIBIDO,
                Pedido.ESTADO_EN_PREPARACION,
                Pedido.ESTADO_LISTO_DESPACHO,
            ]
            return qs.filter(estado__in=estados).order_by("creado")
        if user.has_perm("pedidos.ver_reportes") or user.is_staff:
            return qs.exclude(estado=Pedido.ESTADO_CARRITO).order_by("creado")
        # Cliente: solo sus pedidos, sin carrito ni pendientes de pago
        estados_cliente = [
            Pedido.ESTADO_RECIBIDO,
            Pedido.ESTADO_EN_PREPARACION,
            Pedido.ESTADO_LISTO_DESPACHO,
            Pedido.ESTADO_EN_CAMINO,
            Pedido.ESTADO_ENTREGADO,
        ]
        return qs.filter(cliente=user, estado__in=estados_cliente).order_by("-creado")


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["historial"] = self.object.historial.all()
        return ctx


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    permission_required = None  # se valida por rol en form_valid
    form_class = EstadoPedidoForm
    template_name = "pedidos/pedido_estado.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.has_perm("pedidos.preparar_pedido")
                or request.user.has_perm("pedidos.despachar_pedido")):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        kwargs["pedido"] = pedido
        # determinar siguiente estado permitido segun rol y estado actual
        from .services import TRANSICIONES
        siguientes = TRANSICIONES.get(pedido.estado, [])
        if self.request.user.has_perm("pedidos.preparar_pedido") and pedido.estado in [
            Pedido.ESTADO_RECIBIDO, Pedido.ESTADO_EN_PREPARACION,
        ]:
            kwargs["siguiente_estado"] = siguientes[0] if siguientes else None
        elif self.request.user.has_perm("pedidos.despachar_pedido") and pedido.estado == Pedido.ESTADO_LISTO_DESPACHO:
            kwargs["siguiente_estado"] = siguientes[0] if siguientes else None
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pedido"] = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        return ctx

    def form_valid(self, form):
        pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        nuevo_estado = form.cleaned_data["estado"]
        try:
            avanzar_pedido(pedido, nuevo_estado, self.request.user)
            messages.success(self.request, f"Estado cambiado a {nuevo_estado}.")
        except Exception as exc:
            messages.error(self.request, str(exc))
        return redirect("pedidos:pedido_detail", pk=pedido.pk)

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.kwargs["pk"]})
