"""Vistas de la app pedidos segun docs/reglas_vistas_templates.md y docs/reglas_flujo.md."""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.cuentas.models import Direccion
from apps.pedidos.servicios import (
    avanzar_pedido,
    aplicar_codigo,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
    registrar_estado,
)
from .forms import (
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
    QuitarItemForm,
)
from .models import HistorialEstado, ItemPedido, Pedido


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        context["pedido"] = pedido
        items = []
        for item in pedido.items.all():
            items.append({
                "item": item,
                "subtotal": item.cantidad * item.precio_unitario,
            })
        context["items"] = items
        from apps.pedidos.forms import CodigoForm

        context["codigo_form"] = CodigoForm()
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    form_class = QuitarItemForm
    template_name = "pedidos/item_quitar_form.html"
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        item = get_object_or_404(ItemPedido, pk=self.kwargs["pk"])
        if item.pedido.cliente_id != self.request.user.pk:
            form.add_error(None, "El item no pertenece a tu carrito.")
            return self.form_invalid(form)
        try:
            quitar_item(item)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    form_class = CodigoForm
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data["texto"])
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/carrito_confirmar.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.pedido = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(
                self.pedido,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        metodo = self.request.POST.get("metodo_pago")
        if metodo == "tarjeta":
            return reverse("pagos:pasarela", kwargs={"referencia": self.pedido.pago.referencia})
        return reverse_lazy("pedidos:pedido_list")


class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm("pedidos.ver_reportes") or user.is_staff:
            # Administrador y Dueno: todos menos carrito
            qs = Pedido.objects.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")
        elif user.has_perm("pedidos.preparar_pedido"):
            # Barista: recibido, en_preparacion, listo_despacho, del mas antiguo al mas nuevo
            qs = Pedido.objects.filter(
                estado__in=[
                    Pedido.Estado.RECIBIDO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO,
                ]
            ).order_by("creado")
        elif user.has_perm("pedidos.despachar_pedido"):
            # Repartidor: los listo_despacho, y los en_camino y entregado que son suyos
            from apps.entregas.models import Entrega

            entregas_suyas = Entrega.objects.filter(repartidor=user).values_list(
                "pedido_id", flat=True
            )
            qs = Pedido.objects.filter(
                estado=Pedido.Estado.LISTO_DESPACHO
            ).union(
                Pedido.objects.filter(
                    estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                    pk__in=entregas_suyas,
                )
            ).order_by("-creado")
        else:
            # Cliente: sus pedidos, excluidos carrito y pendientes de pago
            qs = Pedido.objects.filter(cliente=user).exclude(
                estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
            ).order_by("-creado")
        return qs


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.view_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all()
        items_con_subtotal = []
        for item in self.object.items.all():
            items_con_subtotal.append({
                "item": item,
                "subtotal": item.cantidad * item.precio_unitario,
            })
        context["items_con_subtotal"] = items_con_subtotal
        return context


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/pedido_estado.html"

    def has_permission(self):
        return (
            self.request.user.has_perm("pedidos.preparar_pedido")
            or self.request.user.has_perm("pedidos.despachar_pedido")
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        from apps.pedidos.servicios import TRANSICIONES

        estado_actual = self.pedido.estado
        permitidas = TRANSICIONES.get(estado_actual, [])
        user = self.request.user
        opciones = []
        for estado in permitidas:
            if estado in (
                Pedido.Estado.EN_PREPARACION,
                Pedido.Estado.LISTO_DESPACHO,
            ):
                if user.has_perm("pedidos.preparar_pedido"):
                    opciones.append((estado, self.pedido.Estado(estado).label))
            elif estado == Pedido.Estado.EN_CAMINO:
                if user.has_perm("pedidos.despachar_pedido"):
                    opciones.append((estado, self.pedido.Estado(estado).label))
            elif estado == Pedido.Estado.ENTREGADO:
                if user.has_perm("pedidos.despachar_pedido"):
                    opciones.append((estado, self.pedido.Estado(estado).label))
        kwargs["estados_permitidos"] = opciones
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.pedido
        return context

    def form_valid(self, form):
        nuevo_estado = form.cleaned_data["estado"]
        try:
            avanzar_pedido(self.pedido, nuevo_estado, self.request.user)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})
