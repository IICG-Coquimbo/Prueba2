from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from .forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from .models import ItemPedido, Pedido
from .servicios import (
    TRANSICIONES,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


def pedidos_visibles(usuario):
    pedidos = (
        Pedido.objects.select_related("cliente", "direccion")
        .prefetch_related("items")
    )
    if usuario.has_perm("pedidos.ver_reportes"):
        return pedidos.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")
    if usuario.has_perm("pedidos.despachar_pedido"):
        return (
            pedidos.filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO)
                | Q(
                    estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                    entrega__repartidor=usuario,
                )
            )
            .distinct()
            .order_by("creado")
        )
    if usuario.has_perm("pedidos.preparar_pedido"):
        return pedidos.filter(
            estado__in=[
                Pedido.Estado.RECIBIDO,
                Pedido.Estado.EN_PREPARACION,
                Pedido.Estado.LISTO_DESPACHO,
            ]
        ).order_by("creado")
    if usuario.has_perm("pedidos.add_pedido"):
        return (
            pedidos.filter(cliente=usuario)
            .exclude(
                estado__in=[
                    Pedido.Estado.CARRITO,
                    Pedido.Estado.PENDIENTE_PAGO,
                ]
            )
            .order_by("-creado")
        )
    return pedidos.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")


def estados_permitidos(pedido, usuario):
    estados = []
    for estado in TRANSICIONES.get(pedido.estado, []):
        if estado in (Pedido.Estado.CARRITO, Pedido.Estado.RECIBIDO):
            continue
        if estado in (Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO):
            if not usuario.has_perm("pedidos.preparar_pedido"):
                continue
        if estado in (Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO):
            if not usuario.has_perm("pedidos.despachar_pedido"):
                continue
        estados.append(estado)
    return estados


class CarritoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    template_name = "pedidos/carrito_detail.html"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_codigo"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(usuario=self.request.user)
        return context


class CarritoCodigoView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    success_url = reverse_lazy("pedidos:carrito_detail")
    success_message = "Código de descuento aplicado."
    extra_context = {"titulo": "Aplicar código", "accion": "Aplicar"}

    def form_valid(self, form):
        try:
            aplicar_codigo(
                obtener_carrito(self.request.user),
                form.cleaned_data["codigo"],
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        return super().form_valid(form)


class CarritoConfirmarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    success_message = "Pedido confirmado."
    extra_context = {"titulo": "Confirmar pedido", "accion": "Confirmar"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.pago = confirmar_pedido(
                obtener_carrito(self.request.user),
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        if self.pago.metodo == Pedido.MetodoPago.TARJETA:
            return reverse(
                "pagos:pasarela",
                kwargs={"referencia": self.pago.referencia},
            )
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})


class ItemQuitarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    success_url = reverse_lazy("pedidos:carrito_detail")
    success_message = "Producto quitado del carrito."
    extra_context = {"titulo": "Quitar producto", "accion": "Quitar"}

    def get_item(self):
        if not hasattr(self, "item"):
            self.item = get_object_or_404(
                ItemPedido,
                pk=self.kwargs["pk"],
                pedido__cliente=self.request.user,
                pedido__estado=Pedido.Estado.CARRITO,
            )
        return self.item

    def form_valid(self, form):
        try:
            quitar_item(self.get_item())
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        return super().form_valid(form)


class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    permission_required = "pedidos.view_pedido"
    raise_exception = True
    template_name = "pedidos/pedido_list.html"

    def get_queryset(self):
        return pedidos_visibles(self.request.user)


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    permission_required = "pedidos.view_pedido"
    raise_exception = True
    template_name = "pedidos/pedido_detail.html"

    def get_queryset(self):
        return pedidos_visibles(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = (
            self.object.historial.select_related("usuario").order_by("-fecha")
        )
        context["estados_permitidos"] = estados_permitidos(
            self.object, self.request.user
        )
        context["puede_cambiar_estado"] = bool(context["estados_permitidos"])
        context["ver_datos_cliente"] = (
            self.request.user.has_perm("pedidos.despachar_pedido")
            or self.request.user.is_staff
        )
        return context


class PedidoEstadoView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"
    permission_required = ("pedidos.preparar_pedido", "pedidos.despachar_pedido")
    raise_exception = True
    success_message = "Estado del pedido actualizado."
    extra_context = {"titulo": "Cambiar estado", "accion": "Cambiar estado"}

    def has_permission(self):
        return any(
            self.request.user.has_perm(permiso)
            for permiso in self.get_permission_required()
        )

    def get_pedido(self):
        if not hasattr(self, "pedido"):
            self.pedido = get_object_or_404(
                pedidos_visibles(self.request.user),
                pk=self.kwargs["pk"],
            )
        return self.pedido

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["estados"] = estados_permitidos(
            self.get_pedido(), self.request.user
        )
        return kwargs

    def form_valid(self, form):
        try:
            avanzar_pedido(
                self.get_pedido(),
                form.cleaned_data["estado"],
                self.request.user,
            )
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.kwargs["pk"]})


class EntregaListView(PermissionRequiredMixin, ListView):
    model = Pedido
    permission_required = "pedidos.despachar_pedido"
    raise_exception = True
    template_name = "pedidos/entrega_list.html"

    def get_queryset(self):
        return (
            Pedido.objects.filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO)
                | Q(
                    estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                    entrega__repartidor=self.request.user,
                )
            )
            .select_related("cliente", "direccion")
            .prefetch_related("items")
            .distinct()
            .order_by("creado")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ver_datos_cliente"] = True
        return context
