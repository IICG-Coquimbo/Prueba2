from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .models import Pedido, ItemPedido, EstadoPedido
from .forms import EstadoPedidoForm, QuitarItemForm, CodigoForm, ConfirmarPedidoForm
from .servicios import (
    obtener_carrito, quitar_item, aplicar_codigo,
    confirmar_pedido, avanzar_pedido, TRANSICIONES,
)


class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.all().exclude(estado=EstadoPedido.CARRITO)
        if user.has_perm("pedidos.ver_reportes") or user.is_staff:
            return qs
        if user.has_perm("pedidos.despachar_pedido"):
            return qs.filter(
                Q(estado=EstadoPedido.LISTO_DESPACHO)
                | Q(
                    estado__in=[EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO],
                    entrega__repartidor=user,
                )
            ).distinct()
        if user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(
                estado__in=[
                    EstadoPedido.RECIBIDO,
                    EstadoPedido.EN_PREPARACION,
                    EstadoPedido.LISTO_DESPACHO,
                ]
            ).order_by("creado")
        return qs.filter(cliente=user).exclude(
            estado=EstadoPedido.PENDIENTE_PAGO
        )


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.all()
        if not (
            user.has_perm("pedidos.ver_reportes")
            or user.is_staff
            or user.has_perm("pedidos.despachar_pedido")
            or user.has_perm("pedidos.preparar_pedido")
        ):
            qs = qs.filter(cliente=user)
        return qs


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/pedido_estado.html"
    permission_required = None

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        perms = []
        if request.user.has_perm("pedidos.preparar_pedido"):
            perms.append("pedidos.preparar_pedido")
        if request.user.has_perm("pedidos.despachar_pedido"):
            perms.append("pedidos.despachar_pedido")
        if not perms:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        self.permission_required = tuple(perms)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        estados_permitidos = []
        for destino in TRANSICIONES.get(self.pedido.estado, []):
            if destino in (
                EstadoPedido.EN_PREPARACION,
                EstadoPedido.LISTO_DESPACHO,
            ):
                if self.request.user.has_perm("pedidos.preparar_pedido"):
                    estados_permitidos.append((destino, destino.label))
            elif destino in (EstadoPedido.EN_CAMINO, EstadoPedido.ENTREGADO):
                if self.request.user.has_perm("pedidos.despachar_pedido"):
                    estados_permitidos.append((destino, destino.label))
        kwargs["estados_permitidos"] = estados_permitidos
        return kwargs

    def form_valid(self, form):
        nuevo_estado = form.cleaned_data["estado"]
        try:
            avanzar_pedido(self.pedido, nuevo_estado, self.request.user)
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carrito = obtener_carrito(self.request.user)
        context["carrito"] = carrito
        context["items"] = carrito.items.all()
        context["form_codigo"] = CodigoForm()
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    form_class = QuitarItemForm
    template_name = "pedidos/item_quitar.html"
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(ItemPedido, pk=kwargs["pk"])
        if self.item.pedido.cliente_id != request.user.id:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {}

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    form_class = CodigoForm
    template_name = "pedidos/carrito_codigo.html"
    permission_required = "pedidos.add_pedido"

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["codigo"])
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
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
            form.add_error(None, exc.message)
            return self.form_invalid(form)
        return redirect("pedidos:pedido_detail", pk=carrito.pk)

    def get_success_url(self):
        carrito = obtener_carrito(self.request.user)
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": carrito.pk})
