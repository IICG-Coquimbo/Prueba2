from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.pedidos.forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from apps.pedidos.models import EstadoPedido, ItemPedido, Pedido
from apps.pedidos.servicios import (
    TRANSICIONES,
    TRANSICIONES_DESPACHO,
    TRANSICIONES_PREPARACION,
    agregar_item,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


def pedidos_visibles(usuario):
    if usuario.is_staff or usuario.has_perm("pedidos.ver_reportes"):
        return Pedido.objects.exclude(estado=EstadoPedido.CARRITO).order_by("-creado")
    if usuario.has_perm("pedidos.add_pedido"):
        return Pedido.objects.filter(cliente=usuario).exclude(
            estado__in=[EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO]
        ).order_by("-creado")
    if usuario.has_perm("pedidos.despachar_pedido"):
        return Pedido.objects.filter(
            Q(estado=EstadoPedido.LISTO_DESPACHO)
            | Q(
                estado__in=[EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO],
                entrega__repartidor=usuario,
            )
        ).distinct().order_by("-creado")
    if usuario.has_perm("pedidos.preparar_pedido"):
        return Pedido.objects.filter(
            estado__in=[
                EstadoPedido.RECIBIDO,
                EstadoPedido.EN_PREPARACION,
                EstadoPedido.LISTO_DESPACHO,
            ]
        ).order_by("creado")
    return Pedido.objects.none()


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.add_pedido"
    template_name = "pedidos/carrito_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        context["pedido"] = pedido
        context["items"] = pedido.items.select_related("producto").prefetch_related("opciones")
        context["codigo_form"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(self.request.user)
        context["titulo"] = "Carrito"
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            ItemPedido,
            pk=self.kwargs["pk"],
            pedido__cliente=request.user,
            pedido__estado=EstadoPedido.CARRITO,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Quitar item"
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Item eliminado del carrito.")
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Aplicar codigo"
        return context

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data["codigo"])
        except ValidationError as e:
            form.add_error(None, str(e))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Confirmar pedido"
        return context

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            self.pago = confirmar_pedido(
                pedido,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Pedido confirmado.")
        if self.pago.metodo == "tarjeta":
            return redirect("pagos:pasarela", referencia=self.pago.referencia)
        return redirect("pedidos:pedido_detail", pk=pedido.pk)


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"

    def get_queryset(self):
        return pedidos_visibles(self.request.user)


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"

    def get_queryset(self):
        return (
            pedidos_visibles(self.request.user)
            .select_related("cliente", "direccion")
            .prefetch_related("items__opciones", "items__producto", "historial")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["mostrar_contacto"] = user.has_perm("pedidos.despachar_pedido") or user.is_staff
        return context


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    permission_required = ["pedidos.preparar_pedido", "pedidos.despachar_pedido"]
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def has_permission(self):
        perms = self.get_permission_required()
        return any(self.request.user.has_perm(p) for p in perms)

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(pedidos_visibles(request.user), pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def _estados_permitidos(self):
        user = self.request.user
        estados = []
        for t in TRANSICIONES.get(self.pedido.estado, []):
            transicion = (self.pedido.estado, t)
            if transicion in TRANSICIONES_PREPARACION and user.has_perm("pedidos.preparar_pedido"):
                estados.append((t, EstadoPedido(t).label))
            elif transicion in TRANSICIONES_DESPACHO and user.has_perm("pedidos.despachar_pedido"):
                estados.append((t, EstadoPedido(t).label))
        return estados

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["estados"] = self._estados_permitidos()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Cambiar estado"
        context["pedido"] = self.pedido
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, "Estado actualizado.")
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)
