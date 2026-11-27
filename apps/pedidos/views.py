from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .forms import (
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
    QuitarItemForm,
)
from .models import EstadoPedido, ItemPedido, MetodoPago, Pedido
from .servicios import (
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)

ESTADOS_PREPARACION = (
    EstadoPedido.RECIBIDO,
    EstadoPedido.EN_PREPARACION,
    EstadoPedido.LISTO_DESPACHO,
)
ESTADOS_PROPIOS_REPARTIDOR = (EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO)


def _pedidos_visibles(usuario, ocultar_carrito_cliente=False):
    """Filtro de "Quien ve que pedido" (docs/reglas_flujo.md)."""
    queryset = (
        Pedido.objects.select_related("cliente", "direccion")
        .prefetch_related("items")
        .order_by("-creado", "-pk")
    )
    # Administrador y Dueno: todos menos carrito.
    if usuario.has_perm("pedidos.ver_reportes"):
        return queryset.exclude(estado=EstadoPedido.CARRITO)
    # Repartidor: listo_despacho y los que ya estan a su cargo.
    if usuario.has_perm("pedidos.despachar_pedido"):
        return queryset.filter(
            Q(estado=EstadoPedido.LISTO_DESPACHO)
            | Q(estado__in=ESTADOS_PROPIOS_REPARTIDOR, entrega__repartidor=usuario)
        ).distinct()
    # Barista: los que estan en preparacion, del mas antiguo al mas nuevo.
    if usuario.has_perm("pedidos.preparar_pedido"):
        return queryset.filter(estado__in=ESTADOS_PREPARACION).order_by("creado", "pk")
    # Cliente: solo los suyos; en "Mis pedidos" no aparecen carrito ni
    # pendiente de pago (el carrito se ve en /carrito/).
    queryset = queryset.filter(cliente=usuario)
    if ocultar_carrito_cliente:
        queryset = queryset.exclude(
            estado__in=(EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO)
        )
    return queryset


class PedidoCarritoView(PermissionRequiredMixin, TemplateView):
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        context["pedido"] = pedido
        context["object"] = pedido
        context["items"] = pedido.items.select_related("producto").prefetch_related(
            "opciones"
        )
        context["subtotal"] = pedido.subtotal
        context["descuento"] = pedido.descuento
        context["total"] = pedido.total
        context["form"] = CodigoForm()
        return context


class ItemPedidoQuitarView(PermissionRequiredMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = QuitarItemForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            ItemPedido,
            pk=kwargs["pk"],
            pedido__cliente=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accion"] = "quitar"
        context["item"] = self.item
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class PedidoCodigoView(PermissionRequiredMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = CodigoForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.pedido = obtener_carrito(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accion"] = "codigo"
        context["pedido"] = self.pedido
        return context

    def form_valid(self, form):
        try:
            aplicar_codigo(self.pedido, form.cleaned_data["codigo"])
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class PedidoConfirmarView(PermissionRequiredMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = ConfirmarPedidoForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.pedido = obtener_carrito(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accion"] = "confirmar"
        context["pedido"] = self.pedido
        return context

    def form_valid(self, form):
        try:
            self.pago = confirmar_pedido(
                self.pedido,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        if self.pago.metodo == MetodoPago.TARJETA:
            return reverse_lazy(
                "pagos:pasarela", kwargs={"referencia": self.pago.referencia}
            )
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})


class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        return _pedidos_visibles(
            self.request.user, ocultar_carrito_cliente=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        context["vista_tarjetas"] = not usuario.is_staff and (
            usuario.has_perm("pedidos.preparar_pedido")
            or usuario.has_perm("pedidos.despachar_pedido")
        )
        return context


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        return _pedidos_visibles(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        context["items"] = self.object.items.select_related("producto").prefetch_related(
            "opciones"
        )
        context["historial"] = self.object.historial.select_related("usuario").order_by(
            "-fecha", "-pk"
        )
        context["mostrar_datos_cliente"] = (
            usuario.is_staff
            or usuario.is_superuser
            or usuario.has_perm("pedidos.despachar_pedido")
        )
        return context


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = EstadoPedidoForm
    permission_required = (
        "pedidos.preparar_pedido",
        "pedidos.despachar_pedido",
    )

    def has_permission(self):
        usuario = self.request.user
        return usuario.is_active and any(
            usuario.has_perm(permiso) for permiso in self.get_permission_required()
        )

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.pedido
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accion"] = "estado"
        context["pedido"] = self.pedido
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(
                self.pedido,
                form.cleaned_data["estado"],
                self.request.user,
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "pedidos:pedido_detail", kwargs={"pk": self.pedido.pk}
        )
