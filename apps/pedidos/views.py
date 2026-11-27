from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm, QuitarItemForm
from apps.pedidos.models import ItemPedido, Pedido
from apps.pedidos.servicios import (
    PERMISOS_TRANSICION,
    TRANSICIONES,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


class CarritoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"
    context_object_name = "pedido"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_codigo"] = CodigoForm()
        context["form_confirmar"] = ConfirmarPedidoForm(usuario=self.request.user)
        context["form_quitar"] = QuitarItemForm()
        return context


class ItemQuitarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_message = "Item eliminado del carrito."
    success_url = reverse_lazy("pedidos:carrito_detail")

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            ItemPedido, pk=kwargs["pk"], pedido__cliente=request.user, pedido__estado="carrito"
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Quitar {self.item.producto.nombre}"
        context["boton_texto"] = "Quitar del carrito"
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as exc:
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)


class CarritoCodigoView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_message = "Código de descuento aplicado."
    success_url = reverse_lazy("pedidos:carrito_detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Aplicar código de descuento"
        context["boton_texto"] = "Aplicar código"
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["codigo"])
        except ValidationError as exc:
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)


class CarritoConfirmarView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = ConfirmarPedidoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    success_message = "Pedido confirmado."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Confirmar pedido"
        context["boton_texto"] = "Confirmar pedido"
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
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        self.pago = pago
        self.pedido_confirmado = carrito
        return super().form_valid(form)

    def get_success_url(self):
        if self.pago.metodo == "tarjeta":
            return reverse("pagos:pasarela", kwargs={"referencia": self.pago.referencia})
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido_confirmado.pk})


class PedidoListView(PermissionRequiredMixin, ListView):
    model = Pedido
    permission_required = "pedidos.view_pedido"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.select_related("cliente", "direccion").prefetch_related(
            "items__producto", "items__opciones"
        )
        if user.has_perm("pedidos.despachar_pedido") and not user.is_staff and not user.has_perm("pedidos.ver_reportes") and not user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(
                Q(estado="listo_despacho") | Q(estado__in=["en_camino", "entregado"], entrega__repartidor=user)
            ).distinct().order_by("-creado")
        if user.has_perm("pedidos.preparar_pedido") and not user.is_staff and not user.has_perm("pedidos.ver_reportes"):
            return qs.filter(estado__in=["recibido", "en_preparacion", "listo_despacho"]).order_by("creado")
        if user.is_staff or user.has_perm("pedidos.ver_reportes"):
            return qs.exclude(estado="carrito").order_by("-creado")
        return qs.filter(cliente=user).exclude(estado__in=["carrito", "pendiente_pago"]).order_by("-creado")


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    model = Pedido
    permission_required = "pedidos.view_pedido"
    context_object_name = "pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.select_related("cliente", "direccion", "entrega__repartidor").prefetch_related(
            "items__producto", "items__opciones", "historial__usuario"
        )
        if user.has_perm("pedidos.despachar_pedido") and not user.is_staff and not user.has_perm("pedidos.ver_reportes") and not user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(
                Q(estado="listo_despacho") | Q(estado__in=["en_camino", "entregado"], entrega__repartidor=user)
            ).distinct()
        if user.has_perm("pedidos.preparar_pedido") and not user.is_staff and not user.has_perm("pedidos.ver_reportes"):
            return qs.filter(estado__in=["recibido", "en_preparacion", "listo_despacho"])
        if user.is_staff or user.has_perm("pedidos.ver_reportes"):
            return qs.exclude(estado="carrito")
        return qs.filter(cliente=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["puede_ver_direccion"] = user.has_perm("pedidos.despachar_pedido") or user.is_staff
        estados_siguientes = TRANSICIONES.get(self.object.estado, ())
        estados_permitidos = []
        for estado in estados_siguientes:
            permiso = PERMISOS_TRANSICION.get((self.object.estado, estado))
            if permiso and user.has_perm(permiso):
                if (self.object.estado, estado) == ("en_camino", "entregado"):
                    entrega = getattr(self.object, "entrega", None)
                    if entrega and entrega.repartidor_id == user.pk:
                        estados_permitidos.append(estado)
                else:
                    estados_permitidos.append(estado)
        context["estados_permitidos"] = estados_permitidos
        return context


class PedidoEstadoView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"
    permission_required = "pedidos.view_pedido"
    success_message = "Estado del pedido actualizado."

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if not super().has_permission():
            return False
        return len(self._estados_permitidos()) > 0

    def _estados_permitidos(self):
        user = self.request.user
        estados_siguientes = TRANSICIONES.get(self.pedido.estado, ())
        permitidos = []
        for estado in estados_siguientes:
            permiso = PERMISOS_TRANSICION.get((self.pedido.estado, estado))
            if permiso and user.has_perm(permiso):
                if (self.pedido.estado, estado) == ("en_camino", "entregado"):
                    entrega = getattr(self.pedido, "entrega", None)
                    if entrega and entrega.repartidor_id == user.pk:
                        permitidos.append(estado)
                else:
                    permitidos.append(estado)
        return permitidos

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["estados"] = self._estados_permitidos()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Cambiar estado del pedido #{self.pedido.pk}"
        context["boton_texto"] = "Actualizar estado"
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as exc:
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})
