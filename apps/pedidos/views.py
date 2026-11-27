from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView,
)
from django.contrib import messages

from .models import Pedido, ItemPedido, HistorialEstado
from .forms import (
    PedidoForm, ItemPedidoForm, HistorialEstadoForm,
    AgregarAlCarritoForm, QuitarItemForm, CodigoForm,
    ConfirmarPedidoForm, EstadoPedidoForm,
)
from .servicios import (
    obtener_carrito, agregar_item, quitar_item, aplicar_codigo,
    confirmar_pedido, avanzar_pedido, registrar_estado,
    ventas_periodo, productos_mas_pedidos, ranking_repartidores,
    TRANSICIONES,
)
from apps.catalogo.models import Producto
from apps.pagos.forms import PasarelaForm
from apps.pagos.servicios import resultado_pago
from apps.pagos.models import Pago


# ============================================================
# Acciones del flujo (docs/reglas_flujo.md)
# ============================================================

class ProductoAgregarView(PermissionRequiredMixin, FormView):
    form_class = AgregarAlCarritoForm
    template_name = "parciales/accion_form.html"
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        opciones = []
        for tipo in ["tamano", "leche", "azucar"]:
            clave = f"opcion_{tipo}"
            if clave in form.cleaned_data and form.cleaned_data[clave]:
                opciones.append(form.cleaned_data[clave].pk)
        try:
            agregar_item(
                pedido, self.producto,
                form.cleaned_data["cantidad"], opciones,
            )
            messages.success(self.request, "Producto agregado al carrito.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        ctx["pedido"] = pedido
        ctx["items"] = pedido.items.all()
        ctx["codigo_form"] = CodigoForm()
        return ctx


class ItemQuitarView(PermissionRequiredMixin, FormView):
    form_class = QuitarItemForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            ItemPedido, pk=kwargs["pk"],
            pedido__cliente=request.user, pedido__estado="carrito"
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            quitar_item(self.item)
            messages.success(self.request, "Item quitado del carrito.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    form_class = CodigoForm
    permission_required = "pedidos.add_pedido"

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data["codigo"])
            messages.success(self.request, "Codigo de descuento aplicado.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

    def get_success_url(self):
        return reverse_lazy("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
    form_class = ConfirmarPedidoForm
    template_name = "parciales/accion_form.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(
                pedido,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
            messages.success(self.request, "Pedido confirmado.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        if pedido.metodo_pago == "tarjeta":
            return redirect("pedidos:pasarela", referencia=pedido.pago.referencia)
        return redirect("pedidos:pedido_list")

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_list")


class PasarelaView(PermissionRequiredMixin, FormView):
    form_class = PasarelaForm
    template_name = "pedidos/pasarela.html"
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.referencia = kwargs["referencia"]
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pago"] = get_object_or_404(Pago, referencia=self.referencia)
        return ctx

    def form_valid(self, form):
        try:
            resultado_pago(self.referencia, form.cleaned_data["resultado"] == "exitoso")
            messages.success(self.request, "Pago procesado.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return redirect("pedidos:pedido_list")

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_list")


# ============================================================
# Listado y detalle de pedidos (filtrado por rol)
# ============================================================

class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "object_list"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.exclude(estado="carrito")
        if user.has_perm("pedidos.preparar_pedido") and not user.has_perm("pedidos.ver_reportes"):
            qs = qs.filter(estado__in=["recibido", "en_preparacion", "listo_despacho"])
        elif user.has_perm("pedidos.despachar_pedido"):
            qs = qs.filter(
                models.Q(estado="listo_despacho") |
                models.Q(estado__in=["en_camino", "entregado"], entrega__repartidor=user)
            ).distinct()
        elif not user.has_perm("pedidos.ver_reportes"):
            qs = qs.filter(cliente=user).exclude(estado="pendiente_pago")
        return qs


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    permission_required = "pedidos.view_pedido"


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "parciales/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        siguientes = TRANSICIONES.get(self.pedido.estado, [])
        if not isinstance(siguientes, list):
            siguientes = [siguientes]
        requiere_preparar = any(s in ["en_preparacion", "listo_despacho"] for s in siguientes)
        requiere_despachar = any(s in ["en_camino", "entregado"] for s in siguientes)
        if requiere_preparar:
            self.permission_required = "pedidos.preparar_pedido"
        elif requiere_despachar:
            self.permission_required = "pedidos.despachar_pedido"
        else:
            self.permission_required = "pedidos.view_pedido"
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = self.pedido
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
            messages.success(self.request, "Estado actualizado.")
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})


# ============================================================
# CRUD estándar para modelos de pedidos
# ============================================================

class PedidoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = Pedido
    form_class = PedidoForm
    template_name = "pedidos/pedido_form.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Pedido creado correctamente."
    permission_required = "pedidos.add_pedido"


class PedidoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Pedido
    form_class = PedidoForm
    template_name = "pedidos/pedido_form.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Pedido actualizado correctamente."
    permission_required = "pedidos.change_pedido"


class PedidoDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Pedido
    template_name = "pedidos/pedido_confirm_delete.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Pedido eliminado correctamente."
    permission_required = "pedidos.delete_pedido"


class ItemPedidoCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = ItemPedido
    form_class = ItemPedidoForm
    template_name = "pedidos/itempedido_form.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Item creado correctamente."
    permission_required = "pedidos.add_itempedido"


class ItemPedidoUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ItemPedido
    form_class = ItemPedidoForm
    template_name = "pedidos/itempedido_form.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Item actualizado correctamente."
    permission_required = "pedidos.change_itempedido"


class ItemPedidoDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ItemPedido
    template_name = "pedidos/itempedido_confirm_delete.html"
    success_url = reverse_lazy("pedidos:pedido_list")
    success_message = "Item eliminado correctamente."
    permission_required = "pedidos.delete_itempedido"


class HistorialEstadoListView(PermissionRequiredMixin, ListView):
    model = HistorialEstado
    template_name = "pedidos/historialestado_list.html"
    context_object_name = "object_list"
    permission_required = "pedidos.view_pedido"
