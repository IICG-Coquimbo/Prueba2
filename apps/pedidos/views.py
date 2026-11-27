from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from .forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from .models import ItemPedido, Pedido
from .servicios import (
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


class PedidoCarritoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.add_pedido"
    model = Pedido
    template_name = "pedidos/carrito_detail.html"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CodigoForm()
        return context


class PedidoItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_form_kwargs(self):
        self.item = get_object_or_404(
            ItemPedido,
            pk=self.kwargs["pk"],
            pedido__cliente=self.request.user,
            pedido__estado=Pedido.Estado.CARRITO,
        )
        return super().get_form_kwargs()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Quitar producto del carrito"
        context["item"] = self.item
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return super().form_valid(form)


class PedidoCarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Aplicar codigo de descuento"
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["codigo"])
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return super().form_valid(form)


class PedidoCarritoConfirmarView(PermissionRequiredMixin, FormView):
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
        carrito = obtener_carrito(self.request.user)
        try:
            pago = confirmar_pedido(
                carrito,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        self.carrito = carrito
        self.pago = pago
        return super().form_valid(form)

    def get_success_url(self):
        if self.carrito.metodo_pago == Pedido.MetodoPago.EFECTIVO:
            return reverse("pedidos:pedido_detail", kwargs={"pk": self.carrito.pk})
        return reverse("pagos:pasarela", kwargs={"referencia": self.pago.referencia})


class PedidoPorRolMixin:
    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("cliente", "direccion")
            .prefetch_related("items__producto", "historial")
        )
        usuario = self.request.user
        if usuario.is_staff:
            return queryset.exclude(estado=Pedido.Estado.CARRITO)
        if usuario.has_perm("pedidos.despachar_pedido"):
            return queryset.filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO)
                | Q(
                    estado__in=(Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO),
                    entrega__repartidor=usuario,
                )
            )
        if usuario.has_perm("pedidos.preparar_pedido"):
            return queryset.filter(
                estado__in=(
                    Pedido.Estado.RECIBIDO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO,
                )
            ).order_by("creado")
        return queryset.filter(cliente=usuario).exclude(
            estado__in=(Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO)
        )


class PedidoListView(PermissionRequiredMixin, PedidoPorRolMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"


class PedidoDetailView(PermissionRequiredMixin, PedidoPorRolMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    permission_required = ("pedidos.preparar_pedido", "pedidos.despachar_pedido")
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def has_permission(self):
        return any(
            self.request.user.has_perm(permiso)
            for permiso in self.get_permission_required()
        )

    def get_form_kwargs(self):
        self.pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        kwargs = super().get_form_kwargs()
        etiquetas = dict(Pedido.Estado.choices)
        estados = []
        if self.request.user.has_perm("pedidos.preparar_pedido"):
            if self.pedido.estado == Pedido.Estado.RECIBIDO:
                estados.append(
                    (
                        Pedido.Estado.EN_PREPARACION,
                        etiquetas[Pedido.Estado.EN_PREPARACION],
                    )
                )
            elif self.pedido.estado == Pedido.Estado.EN_PREPARACION:
                estados.append(
                    (
                        Pedido.Estado.LISTO_DESPACHO,
                        etiquetas[Pedido.Estado.LISTO_DESPACHO],
                    )
                )
        if self.request.user.has_perm("pedidos.despachar_pedido"):
            if self.pedido.estado == Pedido.Estado.LISTO_DESPACHO:
                estados.append(
                    (Pedido.Estado.EN_CAMINO, etiquetas[Pedido.Estado.EN_CAMINO])
                )
            elif self.pedido.estado == Pedido.Estado.EN_CAMINO:
                estados.append(
                    (Pedido.Estado.ENTREGADO, etiquetas[Pedido.Estado.ENTREGADO])
                )
        kwargs["estados"] = estados
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido"] = self.pedido
        context["titulo"] = "Cambiar estado del pedido"
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(
                self.pedido, form.cleaned_data["estado"], self.request.user
            )
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})
