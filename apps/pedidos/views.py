from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import DetailView, FormView, ListView

from apps.pagos.models import Pago

from . import servicios
from .forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from .models import ItemPedido, Pedido


Estado = Pedido.Estado
PERMISO_CARRITO = "pedidos.add_pedido"
PERMISO_PREPARAR = "pedidos.preparar_pedido"
PERMISO_DESPACHAR = "pedidos.despachar_pedido"


class CarritoActualMixin:
    @cached_property
    def carrito(self):
        return servicios.obtener_carrito(self.request.user)


class PedidoVisibleMixin:
    @cached_property
    def puede_preparar(self):
        return self.request.user.has_perm(PERMISO_PREPARAR)

    @cached_property
    def puede_despachar(self):
        return self.request.user.has_perm(PERMISO_DESPACHAR)

    @cached_property
    def vista_operativa(self):
        return self.puede_preparar or self.puede_despachar

    @cached_property
    def ve_todos_los_pedidos(self):
        usuario = self.request.user
        return usuario.is_superuser or usuario.groups.filter(name="Dueno").exists()

    def pedidos_visibles(self, *, detalle=False):
        usuario = self.request.user
        propios = Q(cliente=usuario)
        if self.ve_todos_los_pedidos:
            visibles = ~Q(estado=Estado.CARRITO)
        else:
            visibles = Q(pk__in=[])
            if self.puede_preparar:
                visibles |= Q(estado__in=(Estado.RECIBIDO, Estado.EN_PREPARACION, Estado.LISTO_DESPACHO))
            if self.puede_despachar:
                visibles |= Q(estado=Estado.LISTO_DESPACHO) | Q(
                    estado__in=(Estado.EN_CAMINO, Estado.ENTREGADO), entrega__repartidor=usuario
                )
            if not self.vista_operativa or usuario.has_perm(PERMISO_CARRITO):
                excluidos = (Estado.CARRITO,) if detalle else (Estado.CARRITO, Estado.PENDIENTE_PAGO)
                visibles |= propios & ~Q(estado__in=excluidos)

        if detalle and usuario.has_perm(PERMISO_CARRITO):
            # La pasarela vuelve al detalle incluso si el pedido regresó a carrito.
            visibles |= propios & Q(estado=Estado.CARRITO, pago__estado=Pago.Estado.FALLIDO)

        return Pedido.objects.filter(visibles).select_related("entrega")

    def puede_avanzar(self, pedido):
        if not self.vista_operativa:
            return False
        form = EstadoPedidoForm(pedido=pedido, usuario=self.request.user)
        return bool(form.fields["estado"].choices)


class CarritoDetailView(PermissionRequiredMixin, CarritoActualMixin, DetailView):
    permission_required = PERMISO_CARRITO
    template_name = "pedidos/carrito_detail.html"

    def get_object(self, queryset=None):
        return self.carrito

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            items=self.object.items.select_related("producto").prefetch_related("opciones"),
            form=CodigoForm(pedido=self.object, usuario=self.request.user),
            **kwargs,
        )


class PedidoListView(PermissionRequiredMixin, PedidoVisibleMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido

    def get_queryset(self):
        pedidos = self.pedidos_visibles()
        if self.vista_operativa and not self.request.user.is_superuser:
            return pedidos.prefetch_related("items__producto", "items__opciones").order_by("creado", "pk")
        return pedidos.order_by("-creado", "-pk")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            mostrar_tarjetas=self.vista_operativa and not self.request.user.is_superuser,
            titulo="Pedidos" if self.vista_operativa or self.ve_todos_los_pedidos else "Mis pedidos",
            pedidos_con_avance={pedido.pk for pedido in self.object_list if self.puede_avanzar(pedido)},
        )
        return contexto


class PedidoDetailView(PermissionRequiredMixin, PedidoVisibleMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido

    def get_queryset(self):
        pedidos = self.pedidos_visibles(detalle=True)
        if self.puede_despachar:
            pedidos = pedidos.select_related("direccion", "cliente__perfil")
        return pedidos

    def get_context_data(self, **kwargs):
        pedido = self.object
        contexto = super().get_context_data(
            items=pedido.items.select_related("producto").prefetch_related("opciones"),
            historial=pedido.historial.order_by("fecha", "pk"),
            puede_avanzar=self.puede_avanzar(pedido),
            volver_carrito=pedido.estado == Estado.CARRITO,
            **kwargs,
        )
        if self.puede_despachar:
            perfil = getattr(pedido.cliente, "perfil", None)
            contexto.update(mostrar_contacto=True, direccion=pedido.direccion, telefono=perfil.telefono if perfil else "")
        return contexto


class AccionPedidoMixin:
    template_name = "pedidos/accion_form.html"
    success_message = ""

    def get_context_data(self, **kwargs):
        return super().get_context_data(titulo=self.titulo, etiqueta_boton=self.etiqueta_boton, **kwargs)

    def form_valid(self, form):
        try:
            self.ejecutar(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        respuesta = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return respuesta


class AccionCarritoMixin(AccionPedidoMixin):
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "usuario": self.request.user}


class ItemQuitarView(PermissionRequiredMixin, AccionCarritoMixin, FormView):
    permission_required = PERMISO_CARRITO
    form_class = QuitarItemForm
    titulo = "Quitar producto"
    etiqueta_boton = "Quitar del carrito"
    success_message = "Producto quitado del carrito."

    @cached_property
    def item(self):
        return get_object_or_404(
            ItemPedido.objects.select_related("pedido", "producto"),
            pk=self.kwargs["pk"],
            pedido__cliente=self.request.user,
            pedido__estado=Estado.CARRITO,
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "item": self.item}

    def get_context_data(self, **kwargs):
        return super().get_context_data(item=self.item, **kwargs)

    def ejecutar(self, form):
        servicios.quitar_item(self.item)


class CarritoCodigoView(PermissionRequiredMixin, CarritoActualMixin, AccionCarritoMixin, FormView):
    permission_required = PERMISO_CARRITO
    form_class = CodigoForm
    titulo = "Aplicar código de descuento"
    etiqueta_boton = "Aplicar código"
    success_message = "Código de descuento aplicado."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "pedido": self.carrito}

    def ejecutar(self, form):
        servicios.aplicar_codigo(self.carrito, form.cleaned_data["texto"])


class CarritoConfirmarView(PermissionRequiredMixin, CarritoActualMixin, AccionCarritoMixin, FormView):
    permission_required = PERMISO_CARRITO
    form_class = ConfirmarPedidoForm
    titulo = "Confirmar pedido"
    etiqueta_boton = "Confirmar pedido"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "pedido": self.carrito}

    def get_context_data(self, **kwargs):
        return super().get_context_data(carrito=self.carrito, **kwargs)

    def ejecutar(self, form):
        self.pago = servicios.confirmar_pedido(
            self.carrito, form.cleaned_data["direccion"], form.cleaned_data["metodo_pago"]
        )
        if self.pago.metodo == Pedido.MetodoPago.EFECTIVO:
            self.success_message = "Pedido confirmado. Pagarás en efectivo al recibirlo."

    def get_success_url(self):
        if self.pago.metodo == Pedido.MetodoPago.TARJETA:
            return reverse("pagos:pasarela", kwargs={"referencia": self.pago.referencia})
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})


class PedidoEstadoView(PermissionRequiredMixin, PedidoVisibleMixin, AccionPedidoMixin, FormView):
    permission_required = (PERMISO_PREPARAR, PERMISO_DESPACHAR)
    form_class = EstadoPedidoForm
    titulo = "Cambiar estado"
    etiqueta_boton = "Cambiar estado"
    success_message = "Estado del pedido actualizado."

    def has_permission(self):
        return any(self.request.user.has_perm(permiso) for permiso in self.get_permission_required())

    @cached_property
    def pedido(self):
        return get_object_or_404(self.pedidos_visibles(), pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "pedido": self.pedido, "usuario": self.request.user}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not form.fields["estado"].choices:
            raise PermissionDenied
        return form

    def get_context_data(self, **kwargs):
        return super().get_context_data(pedido=self.pedido, **kwargs)

    def ejecutar(self, form):
        servicios.avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})
