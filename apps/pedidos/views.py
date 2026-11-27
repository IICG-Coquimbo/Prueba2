from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from .forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from .models import ItemPedido, Pedido
from .servicios import (
    EN_CAMINO,
    EN_PREPARACION,
    ENTREGADO,
    LISTO_DESPACHO,
    RECIBIDO,
    TRANSICIONES,
    agregar_item,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)

CARRITO = Pedido.Estado.CARRITO
PENDIENTE_PAGO = Pedido.Estado.PENDIENTE_PAGO

BARISTA_ESTADOS = {RECIBIDO, EN_PREPARACION, LISTO_DESPACHO}


def _puede_ver(user, pedido):
    if user.is_superuser or user.has_perm("pedidos.ver_reportes"):
        return pedido.estado != CARRITO
    if user.has_perm("pedidos.preparar_pedido"):
        return pedido.estado in BARISTA_ESTADOS
    if user.has_perm("pedidos.despachar_pedido"):
        if pedido.estado == LISTO_DESPACHO:
            return True
        if pedido.estado in (EN_CAMINO, ENTREGADO) and pedido.entrega.repartidor_id == user.id:
            return True
        return False
    return pedido.cliente_id == user.id and pedido.estado not in (CARRITO, PENDIENTE_PAGO)


def _siguientes(user, pedido):
    permitidos = set(TRANSICIONES.get(pedido.estado, set()))
    resultado = set()
    if user.is_superuser or user.has_perm("pedidos.ver_reportes"):
        return permitidos - {RECIBIDO, PENDIENTE_PAGO, CARRITO}
    if user.has_perm("pedidos.preparar_pedido"):
        resultado |= permitidos & {EN_PREPARACION, LISTO_DESPACHO}
    if user.has_perm("pedidos.despachar_pedido"):
        resultado |= permitidos & {EN_CAMINO, ENTREGADO}
    return resultado


class CarritoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/carrito_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.add_pedido"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["codigo_form"] = CodigoForm()
        ctx["direcciones"] = self.request.user.direcciones.all()
        return ctx


class ItemQuitarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        item = get_object_or_404(ItemPedido, pk=self.kwargs["pk"], pedido__cliente=self.request.user)
        try:
            quitar_item(item)
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        return redirect(self.success_url)


class CarritoCodigoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["texto"])
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        return redirect(self.success_url)


class CarritoConfirmarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/carrito_confirmar.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(
                carrito,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        pedido = carrito
        if pedido.metodo_pago == Pedido.MetodoPago.TARJETA:
            return redirect(reverse("pagos:pasarela", args=[pedido.pago.referencia]))
        return redirect(reverse("pedidos:pedido_detail", args=[pedido.pk]))


class PedidoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "object_list"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.select_related("cliente", "direccion")
        if user.is_superuser or user.has_perm("pedidos.ver_reportes"):
            return qs.exclude(estado=CARRITO).order_by("-creado")
        if user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(estado__in=BARISTA_ESTADOS).order_by("creado")
        if user.has_perm("pedidos.despachar_pedido"):
            from django.db.models import Q

            return qs.filter(
                Q(estado=LISTO_DESPACHO)
                | Q(entrega__repartidor=user, estado__in=[EN_CAMINO, ENTREGADO])
            ).distinct().order_by("creado")
        return (
            qs.filter(cliente=user)
            .exclude(estado__in=[CARRITO, PENDIENTE_PAGO])
            .order_by("-creado")
        )


class PedidoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        return Pedido.objects.select_related("cliente", "direccion").all()

    def get_object(self, queryset=None):
        pedido = super().get_object(queryset)
        if not _puede_ver(self.request.user, pedido):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return pedido

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pedido = self.object
        user = self.request.user
        ver_contacto = user.is_superuser or user.has_perm("pedidos.despachar_pedido") or user.has_perm("pedidos.ver_reportes")
        ctx["ver_contacto"] = ver_contacto
        ctx["siguientes"] = _siguientes(user, pedido)
        return ctx


class PedidoEstadoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"
    permission_required = ("pedidos.preparar_pedido", "pedidos.despachar_pedido")

    def has_permission(self):
        return self.request.user.has_perm("pedidos.preparar_pedido") or self.request.user.has_perm(
            "pedidos.despachar_pedido"
        ) or self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.pedido
        kwargs["permitidos"] = sorted(_siguientes(self.request.user, self.pedido))
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pedido"] = self.pedido
        return ctx

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        return redirect(reverse("pedidos:pedido_detail", args=[self.pedido.pk]))

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.pedido.pk])
