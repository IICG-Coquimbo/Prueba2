from django.contrib import messages
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


def _pedidos_visibles(usuario, para_detalle=False):
    permisos = (
        'pedidos.add_pedido',
        'pedidos.preparar_pedido',
        'pedidos.despachar_pedido',
    )
    if usuario.is_staff or not any(usuario.has_perm(permiso) for permiso in permisos):
        return (
            Pedido.objects.exclude(estado=Pedido.Estado.CARRITO)
            .select_related('cliente')
            .order_by('-creado')
        )
    if usuario.has_perm('pedidos.add_pedido'):
        queryset = Pedido.objects.filter(cliente=usuario)
        if not para_detalle:
            queryset = queryset.exclude(
                estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
            )
        return queryset.select_related('cliente').order_by('-creado')
    if usuario.has_perm('pedidos.preparar_pedido'):
        return (
            Pedido.objects.filter(
                estado__in=[
                    Pedido.Estado.RECIBIDO,
                    Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO,
                ]
            )
            .select_related('cliente')
            .order_by('creado')
        )
    if usuario.has_perm('pedidos.despachar_pedido'):
        return (
            Pedido.objects.filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO)
                | Q(
                    estado__in=[Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
                    entrega__repartidor=usuario,
                )
            )
            .select_related('cliente')
            .order_by('creado')
        )
    return Pedido.objects.none()


def _opciones_estado(pedido, usuario):
    etiquetas = dict(Pedido.Estado.choices)
    opciones = []
    if usuario.has_perm('pedidos.preparar_pedido'):
        if pedido.estado == Pedido.Estado.RECIBIDO:
            siguiente = Pedido.Estado.EN_PREPARACION
        elif pedido.estado == Pedido.Estado.EN_PREPARACION:
            siguiente = Pedido.Estado.LISTO_DESPACHO
        else:
            siguiente = None
        if siguiente is not None:
            opciones.append((siguiente, etiquetas[siguiente]))
    if usuario.has_perm('pedidos.despachar_pedido'):
        if pedido.estado == Pedido.Estado.LISTO_DESPACHO:
            siguiente = Pedido.Estado.EN_CAMINO
        elif pedido.estado == Pedido.Estado.EN_CAMINO:
            entrega = getattr(pedido, 'entrega', None)
            siguiente = (
                Pedido.Estado.ENTREGADO
                if entrega is not None and entrega.repartidor_id == usuario.pk
                else None
            )
        else:
            siguiente = None
        if siguiente is not None:
            opciones.append((siguiente, etiquetas[siguiente]))
    return opciones


class AccionFormTemplateMixin:
    def get_template_names(self):
        return ['pedidos/accion_form.html', 'accion_form.html']


class CarritoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'pedidos.add_pedido'
    model = Pedido
    template_name = 'pedidos/carrito_detail.html'
    context_object_name = 'pedido'

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.object
        codigo = pedido.codigo_descuento.codigo if pedido.codigo_descuento else ''
        context['form'] = CodigoForm(initial={'texto': codigo})
        context['confirmar_form'] = ConfirmarPedidoForm(self.request.user)
        return context


class ItemQuitarView(PermissionRequiredMixin, AccionFormTemplateMixin, FormView):
    permission_required = 'pedidos.add_pedido'
    form_class = QuitarItemForm
    template_name = 'accion_form.html'
    success_url = reverse_lazy('pedidos:carrito_detail')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Quitar producto'
        return context

    def form_valid(self, form):
        item = get_object_or_404(
            ItemPedido, pk=self.kwargs['pk'], pedido__cliente=self.request.user
        )
        try:
            quitar_item(item)
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, 'Producto quitado del carrito.')
        return super().form_valid(form)


class CarritoCodigoView(PermissionRequiredMixin, AccionFormTemplateMixin, FormView):
    permission_required = 'pedidos.add_pedido'
    form_class = CodigoForm
    template_name = 'accion_form.html'
    success_url = reverse_lazy('pedidos:carrito_detail')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Aplicar codigo de descuento'
        return context

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data['texto'])
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, 'Codigo de descuento aplicado.')
        return super().form_valid(form)


class CarritoConfirmarView(PermissionRequiredMixin, AccionFormTemplateMixin, FormView):
    permission_required = 'pedidos.add_pedido'
    form_class = ConfirmarPedidoForm
    template_name = 'accion_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Confirmar pedido'
        return context

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(
                pedido,
                form.cleaned_data['direccion'],
                form.cleaned_data['metodo_pago'],
            )
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        self.pedido = pedido
        messages.success(self.request, 'Pedido confirmado.')
        return super().form_valid(form)

    def get_success_url(self):
        pedido = self.pedido
        if pedido.metodo_pago == Pedido.MetodoPago.TARJETA:
            return reverse('pagos:pasarela', args=[pedido.pago.referencia])
        return reverse('pedidos:pedido_detail', args=[pedido.pk])


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = 'pedidos.view_pedido'
    model = Pedido
    template_name = 'pedidos/pedido_list.html'
    context_object_name = 'pedidos'

    def get_queryset(self):
        return _pedidos_visibles(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['es_operador'] = (
            self.request.user.has_perm('pedidos.preparar_pedido')
            or self.request.user.has_perm('pedidos.despachar_pedido')
        )
        return context


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'pedidos.view_pedido'
    model = Pedido
    template_name = 'pedidos/pedido_detail.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return _pedidos_visibles(self.request.user, para_detalle=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contexto_usuario = self.request.user
        context['ver_datos_contacto'] = (
            contexto_usuario.has_perm('pedidos.despachar_pedido')
            or contexto_usuario.is_staff
        )
        perfil = getattr(self.object.cliente, 'perfil', None)
        context['telefono'] = perfil.telefono if perfil else ''
        context['puede_cambiar_estado'] = bool(
            _opciones_estado(self.object, contexto_usuario)
        )
        return context


class PedidoEstadoView(PermissionRequiredMixin, AccionFormTemplateMixin, FormView):
    permission_required = ('pedidos.preparar_pedido', 'pedidos.despachar_pedido')
    form_class = EstadoPedidoForm
    template_name = 'accion_form.html'

    def has_permission(self):
        return any(
            self.request.user.has_perm(permiso) for permiso in self.permission_required
        )

    def get_pedido(self):
        if not hasattr(self, 'pedido'):
            self.pedido = get_object_or_404(Pedido, pk=self.kwargs['pk'])
        return self.pedido

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['opciones'] = _opciones_estado(
            self.get_pedido(), self.request.user
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Cambiar estado'
        context['pedido'] = self.get_pedido()
        return context

    def form_valid(self, form):
        pedido = self.get_pedido()
        try:
            avanzar_pedido(
                pedido, form.cleaned_data['estado'], self.request.user
            )
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, 'Estado del pedido actualizado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pedidos:pedido_detail', args=[self.get_pedido().pk])
