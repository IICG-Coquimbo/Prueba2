from decimal import Decimal
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView, FormView

from .models import Pedido, ItemPedido
from .forms import (
    AgregarAlCarritoForm,
    AplicarDescuentoForm,
    ConfirmarPedidoForm,
    QuitarItemForm,
    EstadoPedidoForm,
)
from .servicios import (
    obtener_carrito,
    agregar_item,
    quitar_item,
    aplicar_codigo,
    confirmar_pedido,
    avanzar_pedido,
    TRANSICIONES,
)


class CarritoDetailView(PermissionRequiredMixin, TemplateView):
    """
    Vista del carrito (pedido en estado carrito).
    Muestra items, totales, formulario de código de descuento y formulario de confirmar.
    """
    template_name = 'pedidos/carrito_detail.html'
    permission_required = 'pedidos.add_pedido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido, _ = obtener_carrito(self.request.user)
        context['pedido'] = pedido
        context['items'] = pedido.items.select_related('producto').prefetch_related('opciones')
        context['form_codigo'] = AplicarDescuentoForm()
        context['form_confirmar'] = ConfirmarPedidoForm(user=self.request.user)
        return context


class AgregarAlCarritoView(PermissionRequiredMixin, FormView):
    """
    Agrega un producto al carrito.
    Reusa el template catalogo/producto_detail.html.
    """
    form_class = AgregarAlCarritoForm
    template_name = 'catalogo/producto_detail.html'
    success_url = reverse_lazy('pedidos:carrito_detail')
    permission_required = 'pedidos.add_pedido'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        producto = get_object_or_404(
            self.get_queryset(),
            pk=self.kwargs['producto_id']
        )
        kwargs['producto'] = producto
        return kwargs

    def get_queryset(self):
        from apps.catalogo.models import Producto
        return Producto.objects.filter(disponible=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        producto = get_object_or_404(self.get_queryset(), pk=self.kwargs['producto_id'])
        context['producto'] = producto
        return context

    def form_valid(self, form):
        producto = get_object_or_404(self.get_queryset(), pk=self.kwargs['producto_id'])
        pedido, _ = obtener_carrito(self.request.user)
        cantidad = form.cleaned_data['cantidad']
        opciones = form.cleaned_data['opciones_ids']
        try:
            agregar_item(pedido, producto, cantidad, opciones)
            messages.success(self.request, f"'{producto.nombre}' agregado al carrito.")
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        return super().form_valid(form)


class QuitarItemView(PermissionRequiredMixin, FormView):
    """
    Quita un item del carrito.
    """
    form_class = QuitarItemForm
    template_name = 'pedidos/accion_form.html'
    success_url = reverse_lazy('pedidos:carrito_detail')
    permission_required = 'pedidos.add_pedido'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['item_id'] = self.kwargs['item_id']
        return kwargs

    def form_valid(self, form):
        item = get_object_or_404(ItemPedido.objects.select_related('pedido'), pk=self.kwargs['item_id'])
        if item.pedido.cliente != self.request.user:
            messages.error(self.request, "No tiene permiso para quitar este item.")
            return redirect(self.success_url)
        try:
            quitar_item(item)
            messages.success(self.request, "Item quitado del carrito.")
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        return super().form_valid(form)


class AplicarCodigoView(PermissionRequiredMixin, FormView):
    """
    Aplica un código de descuento al carrito.
    """
    form_class = AplicarDescuentoForm
    template_name = 'pedidos/accion_form.html'
    success_url = reverse_lazy('pedidos:carrito_detail')
    permission_required = 'pedidos.add_pedido'

    def form_valid(self, form):
        pedido, _ = obtener_carrito(self.request.user)
        codigo = form.cleaned_data['codigo']
        try:
            aplicar_codigo(pedido, codigo)
            messages.success(self.request, f"Código '{codigo}' aplicado correctamente.")
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        return super().form_valid(form)


class ConfirmarPedidoView(PermissionRequiredMixin, FormView):
    """
    Confirma el pedido: crea el Pago y cambia el estado según método de pago.
    Efectivo -> recibido (redirige a pedido_detail)
    Tarjeta -> pendiente_pago (redirige a pasarela de pagos)
    """
    form_class = ConfirmarPedidoForm
    template_name = 'pedidos/accion_form.html'
    permission_required = 'pedidos.add_pedido'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        # Se define en form_valid según el método de pago
        return self.success_url_override or reverse_lazy('pedidos:pedido_list')

    def form_valid(self, form):
        pedido, _ = obtener_carrito(self.request.user)
        direccion = form.cleaned_data['direccion']
        metodo_pago = form.cleaned_data['metodo_pago']
        try:
            pago = confirmar_pedido(pedido, direccion, metodo_pago)
            if metodo_pago == Pedido.MetodoPago.EFECTIVO:
                messages.success(self.request, "Pedido confirmado. Estado: Recibido.")
                self.success_url_override = reverse_lazy('pedidos:pedido_detail', kwargs={'pk': pedido.pk})
            else:
                messages.success(self.request, "Pedido confirmado. Redirigiendo a la pasarela de pago...")
                self.success_url_override = reverse_lazy('pagos:pasarela', kwargs={'referencia': pago.referencia})
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        return super().form_valid(form)


class PedidoListView(PermissionRequiredMixin, ListView):
    """
    Lista de pedidos filtrada por rol según reglas_flujo.md.
    """
    model = Pedido
    template_name = 'pedidos/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 20
    permission_required = 'pedidos.view_pedido'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'direccion', 'codigo_descuento').prefetch_related('items__producto')
        user = self.request.user

        if user.has_perm('pedidos.ver_reportes') or user.is_superuser or user.has_perm('pedidos.preparar_pedido') and user.has_perm('pedidos.despachar_pedido'):
            # Administrador/Dueño: todos menos carrito
            return queryset.exclude(estado=Pedido.Estado.CARRITO)

        if user.has_perm('pedidos.preparar_pedido'):
            # Barista: recibido, en_preparacion, listo_despacho
            return queryset.filter(
                estado__in=[
                    Pedido.Estado.RECIBIDO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO,
                ]
            ).order_by('creado')

        if user.has_perm('pedidos.despachar_pedido'):
            # Repartidor: listo_despacho, y en_camino/entregado que son suyos
            return queryset.filter(
                estado__in=[
                    Pedido.Estado.LISTO_DESPACHO,
                    Pedido.Estado.EN_CAMINO,
                    Pedido.Estado.ENTREGADO,
                ]
            ).filter(
                models.Q(estado=Pedido.Estado.LISTO_DESPACHO) |
                models.Q(entrega__repartidor=user)
            ).distinct().order_by('creado')

        # Cliente: sus pedidos sin carrito ni pendiente_pago
        return queryset.filter(cliente=user).exclude(
            estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
        ).order_by('-creado')


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    """
    Detalle del pedido con items, totales, historial y botones de acción según rol.
    """
    model = Pedido
    template_name = 'pedidos/pedido_detail.html'
    context_object_name = 'pedido'
    permission_required = 'pedidos.view_pedido'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'direccion', 'codigo_descuento', 'pago', 'entrega__repartidor').prefetch_related('items__producto', 'items__opciones', 'historial__usuario')
        user = self.request.user

        if user.has_perm('pedidos.ver_reportes') or user.is_superuser:
            return queryset.exclude(estado=Pedido.Estado.CARRITO)

        if user.has_perm('pedidos.preparar_pedido'):
            return queryset.filter(
                estado__in=[
                    Pedido.Estado.RECIBIDO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO,
                ]
            )

        if user.has_perm('pedidos.despachar_pedido'):
            return queryset.filter(
                estado__in=[
                    Pedido.Estado.LISTO_DESPACHO,
                    Pedido.Estado.EN_CAMINO,
                    Pedido.Estado.ENTREGADO,
                ]
            ).filter(
                models.Q(estado=Pedido.Estado.LISTO_DESPACHO) |
                models.Q(entrega__repartidor=user)
            ).distinct()

        # Cliente: solo sus pedidos sin carrito ni pendiente_pago
        return queryset.filter(cliente=user).exclude(
            estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.object
        user = self.request.user

        # Historial de estados
        context['historial'] = pedido.historial.select_related('usuario').order_by('fecha')

        # Botones de acción según rol/permiso y estado actual
        context['puede_preparar'] = user.has_perm('pedidos.preparar_pedido')
        context['puede_despachar'] = user.has_perm('pedidos.despachar_pedido')
        context['es_repartidor_asignado'] = (
            hasattr(pedido, 'entrega') and pedido.entrega.repartidor == user
        )

        # Siguiente estado permitido según TRANSICIONES y rol
        context['estados_siguientes'] = self._get_estados_siguientes(pedido, user)

        # Meta refresh para recarga automática cada 15s (RF-09, RNF-06, RNF-07)
        context['auto_refresh'] = True

        return context

    def _get_estados_siguientes(self, pedido, user):
        """Devuelve lista de (valor, label) de estados siguientes permitidos para el usuario."""
        estados_permitidos = TRANSICIONES.get(pedido.estado, [])
        if not estados_permitidos:
            return []

        siguientes = []
        for estado in estados_permitidos:
            # Validar permiso según el estado destino
            if estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
                if user.has_perm('pedidos.preparar_pedido'):
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado == Pedido.Estado.EN_CAMINO:
                if user.has_perm('pedidos.despachar_pedido'):
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado == Pedido.Estado.ENTREGADO:
                if user.has_perm('pedidos.despachar_pedido') and hasattr(pedido, 'entrega') and pedido.entrega.repartidor == user:
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado in [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO]:
                # Estas transiciones son desde carrito, no deberían aparecer aquí
                pass
        return siguientes


class AvanzarEstadoView(PermissionRequiredMixin, FormView):
    """
    Avanza el estado del pedido según TRANSICIONES y permisos del rol.
    """
    form_class = EstadoPedidoForm
    template_name = 'pedidos/accion_form.html'
    permission_required = 'pedidos.preparar_pedido'  # Se valida en form_valid también

    def get_permission_required(self):
        # Permiso dinámico según la transición
        pedido = get_object_or_404(Pedido, pk=self.kwargs['pk'])
        estados_siguientes = self._get_estados_siguientes(pedido, self.request.user)
        if not estados_siguientes:
            return 'pedidos.preparar_pedido'  # default
        # Verificar qué permiso se necesita para el primer estado siguiente
        primer_estado = estados_siguientes[0][0]
        if primer_estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
            return 'pedidos.preparar_pedido'
        return 'pedidos.despachar_pedido'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pedido = get_object_or_404(Pedido, pk=self.kwargs['pk'])
        estados_siguientes = self._get_estados_siguientes(pedido, self.request.user)
        kwargs['estados_permitidos'] = estados_siguientes
        return kwargs

    def get_success_url(self):
        return reverse_lazy('pedidos:pedido_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pedido'] = get_object_or_404(Pedido, pk=self.kwargs['pk'])
        return context

    def form_valid(self, form):
        pedido = get_object_or_404(Pedido, pk=self.kwargs['pk'])
        nuevo_estado = form.cleaned_data['estado']
        try:
            avanzar_pedido(pedido, nuevo_estado, self.request.user)
            messages.success(self.request, f"Estado cambiado a: {dict(Pedido.Estado.choices).get(nuevo_estado, nuevo_estado)}")
        except ValidationError as e:
            form.add_error(None, e.message)
            return self.form_invalid(form)
        return super().form_valid(form)

    def _get_estados_siguientes(self, pedido, user):
        """Devuelve lista de (valor, label) de estados siguientes permitidos para el usuario."""
        from .servicios import TRANSICIONES
        estados_permitidos = TRANSICIONES.get(pedido.estado, [])
        if not estados_permitidos:
            return []

        siguientes = []
        for estado in estados_permitidos:
            if estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
                if user.has_perm('pedidos.preparar_pedido'):
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado == Pedido.Estado.EN_CAMINO:
                if user.has_perm('pedidos.despachar_pedido'):
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado == Pedido.Estado.ENTREGADO:
                if user.has_perm('pedidos.despachar_pedido') and hasattr(pedido, 'entrega') and pedido.entrega.repartidor == user:
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
        return siguientes