from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado
from apps.pedidos.forms import QuitarItemForm, CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm
from apps.pedidos.servicios import (
    obtener_carrito, quitar_item, aplicar_codigo, confirmar_pedido, avanzar_pedido
)
from apps.cuentas.models import Direccion


class PedidoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"
    paginate_by = 10
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        qs = Pedido.objects.select_related("cliente", "direccion", "codigo_descuento").prefetch_related("items__producto")
        user = self.request.user
        if user.has_perm("pedidos.preparar_pedido"):
            qs = qs.filter(estado__in=[
                Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO
            ]).order_by("creado")
        elif user.has_perm("pedidos.despachar_pedido"):
            qs = qs.filter(estado__in=[
                Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO
            ]).filter(
                models.Q(estado=Pedido.Estado.LISTO_DESPACHO) |
                models.Q(entrega__repartidor=user)
            ).order_by("creado")
        elif user.has_perm("pedidos.ver_reportes") or user.is_staff:
            qs = qs.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")
        else:
            qs = qs.filter(cliente=user).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]).order_by("-creado")
        return qs


class PedidoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente", "direccion", "codigo_descuento").prefetch_related("items__producto", "items__opciones", "historial__usuario", "entrega__repartidor", "pago")
        user = self.request.user
        if user.has_perm("pedidos.preparar_pedido"):
            qs = qs.filter(estado__in=[Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO])
        elif user.has_perm("pedidos.despachar_pedido"):
            qs = qs.filter(estado__in=[Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]).filter(
                models.Q(estado=Pedido.Estado.LISTO_DESPACHO) | models.Q(entrega__repartidor=user)
            )
        elif user.has_perm("pedidos.ver_reportes") or user.is_staff:
            qs = qs.exclude(estado=Pedido.Estado.CARRITO)
        else:
            qs = qs.filter(cliente=user).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all()
        context["puede_ver_datos_cliente"] = self.request.user.has_perm("pedidos.despachar_pedido") or self.request.user.is_staff
        return context


class CarritoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/carrito_detail.html"
    context_object_name = "pedido"
    permission_required = "pedidos.add_pedido"

    def get_object(self):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["codigo_form"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(usuario=self.request.user)
        return context


class ItemQuitarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = QuitarItemForm
    permission_required = "pedidos.add_pedido"

    def form_valid(self, form):
        item = get_object_or_404(ItemPedido, pk=self.kwargs["pk"], pedido__cliente=self.request.user, pedido__estado=Pedido.Estado.CARRITO)
        try:
            quitar_item(item)
            messages.success(self.request, "Item quitado del carrito.")
        except Exception as e:
            messages.error(self.request, str(e))
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = CodigoForm
    permission_required = "pedidos.add_pedido"

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["codigo"])
            messages.success(self.request, "Codigo aplicado correctamente.")
        except Exception as e:
            messages.error(self.request, str(e))
        return redirect("pedidos:carrito_detail")


class CarritoConfirmarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = ConfirmarPedidoForm
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(carrito, form.cleaned_data["direccion"], form.cleaned_data["metodo_pago"])
            if form.cleaned_data["metodo_pago"] == Pedido.MetodoPago.TARJETA:
                return redirect("pagos:pasarela", referencia=carrito.pago.referencia)
            messages.success(self.request, "Pedido confirmado. Estado: Recibido.")
            return redirect("pedidos:pedido_detail", pk=carrito.pk)
        except Exception as e:
            messages.error(self.request, str(e))
            return redirect("pedidos:carrito_detail")


class PedidoEstadoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    permission_required = "pedidos.preparar_pedido"
    template_name = "pedidos/pedido_estado.html"

    def get_permission_required(self):
        pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        if pedido.estado in [Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION]:
            return "pedidos.preparar_pedido"
        return "pedidos.despachar_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pedido"] = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        pedido = get_object_or_404(Pedido, pk=self.kwargs["pk"])
        try:
            avanzar_pedido(pedido, form.cleaned_data["estado"], self.request.user)
            messages.success(self.request, f"Pedido actualizado a: {pedido.get_estado_display()}.")
        except Exception as e:
            messages.error(self.request, str(e))
        return redirect("pedidos:pedido_detail", pk=pedido.pk)


from django.db import models