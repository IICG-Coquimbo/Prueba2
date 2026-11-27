from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import models
from django.views.generic import ListView, DetailView

from .models import Entrega
from apps.pedidos.models import Pedido


class EntregaListView(PermissionRequiredMixin, ListView):
    """
    Lista de entregas filtrada por rol según reglas_flujo.md.
    - Barista: no ve esta vista (no tiene permiso pedidos.despachar_pedido)
    - Repartidor: sus entregas (listo_despacho, en_camino, entregado) + las listo_despacho sin repartidor
    - Admin/Dueño: todas
    """
    model = Entrega
    template_name = 'entregas/entrega_list.html'
    context_object_name = 'entregas'
    paginate_by = 20
    permission_required = 'pedidos.despachar_pedido'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'pedido', 'pedido__cliente', 'pedido__direccion', 'repartidor'
        ).prefetch_related('pedido__items__producto')
        user = self.request.user

        # Administrador/Dueño: todas las entregas
        if user.has_perm('pedidos.ver_reportes') or user.is_superuser:
            return queryset.order_by('-pedido__creado')

        # Repartidor: sus entregas + las listo_despacho sin repartidor
        if user.has_perm('pedidos.despachar_pedido'):
            return queryset.filter(
                models.Q(repartidor=user) |
                models.Q(pedido__estado=Pedido.Estado.LISTO_DESPACHO, repartidor__isnull=True)
            ).distinct().order_by('-pedido__creado')

        # Por defecto (no debería llegar aquí porque Barista no tiene permiso)
        return queryset.none()


class EntregaDetailView(PermissionRequiredMixin, DetailView):
    """
    Detalle de la entrega con info del pedido, items, historial y botones de acción.
    """
    model = Entrega
    template_name = 'entregas/entrega_detail.html'
    context_object_name = 'entrega'
    permission_required = 'pedidos.despachar_pedido'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'pedido', 'pedido__cliente', 'pedido__direccion', 'repartidor'
        ).prefetch_related(
            'pedido__items__producto', 'pedido__items__opciones',
            'pedido__historial__usuario'
        )
        user = self.request.user

        # Administrador/Dueño: todas
        if user.has_perm('pedidos.ver_reportes') or user.is_superuser:
            return queryset

        # Repartidor: solo sus entregas
        if user.has_perm('pedidos.despachar_pedido'):
            return queryset.filter(
                models.Q(repartidor=user) |
                models.Q(pedido__estado=Pedido.Estado.LISTO_DESPACHO, repartidor__isnull=True)
            ).distinct()

        return queryset.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entrega = self.object
        pedido = entrega.pedido
        user = self.request.user

        # Pedido e items
        context['pedido'] = pedido
        context['items'] = pedido.items.select_related('producto').prefetch_related('opciones')

        # Historial de estados del pedido
        context['historial'] = pedido.historial.select_related('usuario').order_by('fecha')

        # Permisos para mostrar teléfono y dirección
        context['puede_ver_contacto'] = user.has_perm('pedidos.despachar_pedido') or user.is_superuser or user.has_perm('pedidos.ver_reportes')

        # Es el repartidor asignado
        context['es_repartidor_asignado'] = entrega.repartidor == user

        # Minutos calculados (propiedad del modelo)
        context['minutos'] = entrega.minutos

        # Estados siguientes permitidos para el repartidor
        context['estados_siguientes'] = self._get_estados_siguientes(pedido, user, entrega)

        return context

    def _get_estados_siguientes(self, pedido, user, entrega):
        """Devuelve lista de (valor, label) de estados siguientes permitidos para el repartidor."""
        from apps.pedidos.servicios import TRANSICIONES

        estados_permitidos = TRANSICIONES.get(pedido.estado, [])
        if not estados_permitidos:
            return []

        siguientes = []
        for estado in estados_permitidos:
            # Solo transiciones de despachar_pedido: listo_despacho -> en_camino, en_camino -> entregado
            if estado == Pedido.Estado.EN_CAMINO:
                # Solo si es listo_despacho y (sin repartidor o es el repartidor asignado)
                if pedido.estado == Pedido.Estado.LISTO_DESPACHO:
                    if not entrega.repartidor or entrega.repartidor == user:
                        siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))
            elif estado == Pedido.Estado.ENTREGADO:
                # Solo el repartidor asignado puede marcar como entregado
                if pedido.estado == Pedido.Estado.EN_CAMINO and entrega.repartidor == user:
                    siguientes.append((estado, dict(Pedido.Estado.choices).get(estado, estado)))

        return siguientes