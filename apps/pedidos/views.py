from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from apps.pedidos.models import EstadoPedido, ItemPedido, MetodoPago, Pedido
from apps.pedidos.servicios import (
    TRANSICIONES,
    avanzar_pedido,
    aplicar_codigo,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


class CarritoDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    permission_required = "pedidos.add_pedido"
    model = Pedido
    template_name = "pedidos/carrito_detail.html"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CodigoForm()
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"

    def form_valid(self, form):
        item = get_object_or_404(
            ItemPedido,
            pk=self.kwargs["pk"],
            pedido__cliente=self.request.user,
            pedido__estado=EstadoPedido.CARRITO,
        )
        try:
            quitar_item(item)
        except ValidationError as e:
            form.add_error(None, str(e.message if hasattr(e, "message") else "; ".join(e.messages)))
            return self.form_invalid(form)
        messages.success(self.request, "Item eliminado del carrito.")
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"

    def form_valid(self, form):
        try:
            aplicar_codigo(obtener_carrito(self.request.user), form.cleaned_data["codigo"])
        except ValidationError as e:
            form.add_error(None, str(e.message if hasattr(e, "message") else "; ".join(e.messages)))
            return self.form_invalid(form)
        messages.success(self.request, "Codigo aplicado.")
        return redirect("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/accion_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            pago = confirmar_pedido(
                carrito,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as e:
            form.add_error(None, str(e.message if hasattr(e, "message") else "; ".join(e.messages)))
            return self.form_invalid(form)
        messages.success(self.request, "Pedido confirmado.")
        if form.cleaned_data["metodo_pago"] == MetodoPago.TARJETA:
            return redirect("pagos:pasarela", referencia=pago.referencia)
        return redirect("pedidos:pedido_detail", pk=pago.pedido_id)


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"

    def get_queryset(self):
        user = self.request.user
        queryset = Pedido.objects.select_related("cliente", "direccion").prefetch_related("items__producto", "items__opciones").all()
        if user.is_staff or user.has_perm("pedidos.ver_reportes"):
            return queryset.exclude(estado=EstadoPedido.CARRITO).order_by("-creado")
        if user.has_perm("pedidos.preparar_pedido"):
            return queryset.filter(
                estado__in=[
                    EstadoPedido.RECIBIDO,
                    EstadoPedido.EN_PREPARACION,
                    EstadoPedido.LISTO_DESPACHO,
                ]
            ).order_by("creado")
        if user.has_perm("pedidos.despachar_pedido"):
            return queryset.filter(
                Q(estado=EstadoPedido.LISTO_DESPACHO)
                | Q(
                    estado__in=[EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO],
                    entrega__repartidor=user,
                )
            ).order_by("-creado")
        return queryset.filter(
            cliente=user,
            estado__in=[
                EstadoPedido.RECIBIDO,
                EstadoPedido.EN_PREPARACION,
                EstadoPedido.LISTO_DESPACHO,
                EstadoPedido.EN_CAMINO,
                EstadoPedido.ENTREGADO,
            ],
        ).order_by("-creado")


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"

    def get_queryset(self):
        user = self.request.user
        queryset = Pedido.objects.select_related("cliente", "direccion", "codigo_descuento").prefetch_related(
            "items__producto", "items__opciones", "historial"
        )
        if (
            user.has_perm("pedidos.preparar_pedido")
            or user.has_perm("pedidos.despachar_pedido")
            or user.has_perm("pedidos.ver_reportes")
            or user.is_staff
        ):
            return queryset
        return queryset.filter(cliente=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all().order_by("fecha")
        return context


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.preparar_pedido"
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("pedidos.preparar_pedido") or user.has_perm("pedidos.despachar_pedido")

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_estados_permitidos(self):
        user = self.request.user
        actuales = TRANSICIONES.get(self.pedido.estado, [])
        if user.is_staff:
            return actuales
        estados = []
        for estado in actuales:
            if user.has_perm("pedidos.preparar_pedido") and self.pedido.estado == EstadoPedido.RECIBIDO and estado == EstadoPedido.EN_PREPARACION:
                estados.append(estado)
            if user.has_perm("pedidos.preparar_pedido") and self.pedido.estado == EstadoPedido.EN_PREPARACION and estado == EstadoPedido.LISTO_DESPACHO:
                estados.append(estado)
            if user.has_perm("pedidos.despachar_pedido") and self.pedido.estado == EstadoPedido.LISTO_DESPACHO and estado == EstadoPedido.EN_CAMINO:
                estados.append(estado)
            if user.has_perm("pedidos.despachar_pedido") and self.pedido.estado == EstadoPedido.EN_CAMINO and estado == EstadoPedido.ENTREGADO:
                estados.append(estado)
        return estados

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["estados"] = self.get_estados_permitidos()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido"] = self.pedido
        context["estados_disponibles"] = self.get_estados_permitidos()
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as e:
            form.add_error(None, str(e.message if hasattr(e, "message") else "; ".join(e.messages)))
            return self.form_invalid(form)
        messages.success(self.request, "Estado actualizado.")
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)
