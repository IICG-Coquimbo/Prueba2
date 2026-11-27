from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.catalogo.models import Producto
from apps.pedidos.models import Pedido

from .forms import (
    AgregarAlCarritoForm,
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
    QuitarItemForm,
)
from .models import ItemPedido
from .servicios import (
    agregar_item,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


def _mensaje(error):
    return error.messages[0] if getattr(error, "messages", None) else str(error)


def _es_admin(usuario):
    return usuario.is_superuser or usuario.groups.filter(name="Administrador").exists()


def pedidos_visibles(usuario):
    queryset = Pedido.objects.select_related("cliente", "direccion").prefetch_related(
        "items__producto", "items__opciones", "historial"
    )
    if _es_admin(usuario) or usuario.has_perm("pedidos.ver_reportes"):
        return queryset.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")
    if usuario.has_perm("pedidos.add_pedido"):
        return queryset.filter(cliente=usuario).exclude(
            estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
        ).order_by("-creado")
    if usuario.has_perm("pedidos.preparar_pedido"):
        return queryset.filter(
            estado__in=[
                Pedido.Estado.RECIBIDO,
                Pedido.Estado.EN_PREPARACION,
                Pedido.Estado.LISTO_DESPACHO,
            ]
        ).order_by("creado")
    if usuario.has_perm("pedidos.despachar_pedido"):
        return queryset.filter(
            Q(estado=Pedido.Estado.LISTO_DESPACHO)
            | Q(
                estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                entrega__repartidor=usuario,
            )
        ).order_by("creado")
    return queryset.none()


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "pedidos/accion_form.html"

    def get_producto(self):
        return get_object_or_404(Producto, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.get_producto()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["producto"] = self.get_producto()
        return context

    def form_valid(self, form):
        opciones = [
            form.cleaned_data[clave]
            for clave in form.cleaned_data
            if clave.startswith("opcion_") and form.cleaned_data[clave]
        ]
        try:
            agregar_item(
                obtener_carrito(self.request.user),
                self.get_producto(),
                form.cleaned_data["cantidad"],
                opciones,
            )
        except ValidationError as error:
            form.add_error(None, _mensaje(error))
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:carrito_detail")


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.add_pedido"
    template_name = "pedidos/carrito_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido"] = obtener_carrito(self.request.user)
        context["codigo_form"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(usuario=self.request.user)
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"

    def get_item(self):
        return get_object_or_404(
            ItemPedido,
            pk=self.kwargs["pk"],
            pedido__cliente=self.request.user,
            pedido__estado=Pedido.Estado.CARRITO,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item"] = self.get_item()
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.get_item())
        except ValidationError as error:
            form.add_error(None, _mensaje(error))
            return self.form_invalid(form)
        messages.success(self.request, "Item quitado del carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"

    def form_valid(self, form):
        try:
            aplicar_codigo(obtener_carrito(self.request.user), form.cleaned_data["texto"])
        except ValidationError as error:
            form.add_error(None, _mensaje(error))
            return self.form_invalid(form)
        messages.success(self.request, "Codigo de descuento aplicado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/accion_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            pedido = confirmar_pedido(
                obtener_carrito(self.request.user),
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as error:
            form.add_error(None, _mensaje(error))
            return self.form_invalid(form)
        self.pedido = pedido
        messages.success(self.request, "Pedido confirmado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.pedido.metodo_pago == Pedido.MetodoPago.TARJETA:
            return reverse("pagos:pasarela", args=[self.pedido.pago.referencia])
        return reverse("pedidos:pedido_detail", args=[self.pedido.pk])


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        return pedidos_visibles(self.request.user)


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    template_name = "pedidos/pedido_detail.html"

    def get_queryset(self):
        usuario = self.request.user
        if usuario.has_perm("pedidos.add_pedido") and not _es_admin(usuario):
            return Pedido.objects.filter(cliente=usuario).prefetch_related(
                "items__producto", "items__opciones", "historial"
            )
        return pedidos_visibles(usuario)


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    permission_required = ()
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def has_permission(self):
        usuario = self.request.user
        return usuario.is_authenticated and (
            usuario.has_perm("pedidos.preparar_pedido")
            or usuario.has_perm("pedidos.despachar_pedido")
        )

    def get_pedido(self):
        return get_object_or_404(Pedido, pk=self.kwargs["pk"])

    def get_opciones(self, pedido):
        usuario = self.request.user
        actual = pedido.estado
        if actual == Pedido.Estado.RECIBIDO and usuario.has_perm("pedidos.preparar_pedido"):
            return [(Pedido.Estado.EN_PREPARACION, "En preparacion")]
        if actual == Pedido.Estado.EN_PREPARACION and usuario.has_perm("pedidos.preparar_pedido"):
            return [(Pedido.Estado.LISTO_DESPACHO, "Listo despacho")]
        if actual == Pedido.Estado.LISTO_DESPACHO and usuario.has_perm("pedidos.despachar_pedido"):
            return [(Pedido.Estado.EN_CAMINO, "En camino")]
        if actual == Pedido.Estado.EN_CAMINO and usuario.has_perm("pedidos.despachar_pedido"):
            entrega = getattr(pedido, "entrega", None)
            if entrega is not None and entrega.repartidor_id == usuario.pk:
                return [(Pedido.Estado.ENTREGADO, "Entregado")]
        return []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["opciones"] = self.get_opciones(self.get_pedido())
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido"] = self.get_pedido()
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(self.get_pedido(), form.cleaned_data["estado"], self.request.user)
        except ValidationError as error:
            form.add_error(None, _mensaje(error))
            return self.form_invalid(form)
        messages.success(self.request, "Estado del pedido actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.kwargs["pk"]])
