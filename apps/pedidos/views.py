from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import (
    AgregarAlCarritoForm,
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
    QuitarItemForm,
)
from apps.pedidos.models import EstadoPedido, ItemPedido, Pedido
from apps.pedidos.servicios import (
    TRANSICIONES,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


def _pedidos_visibles(usuario):
    pedidos = Pedido.objects.exclude(estado="carrito")
    if usuario.is_staff:
        return pedidos
    if usuario.has_perm("pedidos.add_pedido"):
        return pedidos.filter(cliente=usuario).exclude(estado="pendiente_pago")
    if usuario.has_perm("pedidos.preparar_pedido"):
        return pedidos.filter(
            estado__in=("recibido", "en_preparacion", "listo_despacho")
        ).order_by("creado")
    if usuario.has_perm("pedidos.despachar_pedido"):
        return pedidos.filter(
            Q(estado="listo_despacho")
            | Q(
                estado__in=("en_camino", "entregado"),
                entrega__repartidor=usuario,
            )
        ).distinct().order_by("creado")
    return pedidos


class CarritoDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    permission_required = "pedidos.add_pedido"
    model = Pedido
    template_name = "pedidos/carrito.html"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["codigo_form"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(self.request.user)
        context["quitar_form"] = QuitarItemForm()
        return context


class ItemQuitarView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        item = get_object_or_404(
            ItemPedido,
            pk=self.kwargs["pk"],
            pedido__cliente=self.request.user,
            pedido__estado="carrito",
        )
        try:
            quitar_item(item)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Producto quitado del carrito.")
        return super().form_valid(form)


class CarritoCodigoView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        try:
            aplicar_codigo(
                obtener_carrito(self.request.user), form.cleaned_data["codigo"]
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Código de descuento aplicado.")
        return super().form_valid(form)


class CarritoConfirmarView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/accion_form.html"

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
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Pedido confirmado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.pago.metodo == "tarjeta":
            return reverse("pagos:pasarela", args=[self.pago.referencia])
        return reverse("pedidos:pedido_detail", args=[self.pago.pedido_id])


class PedidoListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido

    def get_queryset(self):
        return _pedidos_visibles(self.request.user)


class PedidoDetailView(PermissionRequiredMixin, LoginRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"

    def get_queryset(self):
        return _pedidos_visibles(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all().order_by("fecha")
        context["ver_datos"] = (
            self.request.user.has_perm("pedidos.despachar_pedido")
            or self.request.user.is_staff
        )
        return context


class PedidoEstadoView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def get_permission_required(self):
        if self.request.user.has_perm("pedidos.preparar_pedido"):
            return ["pedidos.preparar_pedido"]
        return ["pedidos.despachar_pedido"]

    def _get_pedido(self):
        return get_object_or_404(Pedido, pk=self.kwargs["pk"])

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.kwargs["pk"]])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pedido = self._get_pedido()
        etiquetas = dict(EstadoPedido.choices)
        if self.request.user.has_perm("pedidos.preparar_pedido"):
            validas = (
                ("recibido", "en_preparacion"),
                ("en_preparacion", "listo_despacho"),
            )
        else:
            validas = (
                ("listo_despacho", "en_camino"),
                ("en_camino", "entregado"),
            )
        kwargs["estados"] = [
            (destino, etiquetas[destino])
            for destino in TRANSICIONES.get(pedido.estado, [])
            if (pedido.estado, destino) in validas
        ]
        return kwargs

    def form_valid(self, form):
        pedido = self._get_pedido()
        try:
            avanzar_pedido(pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Estado del pedido actualizado.")
        return super().form_valid(form)
