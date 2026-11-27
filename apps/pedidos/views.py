from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.catalogo.models import OpcionProducto, Producto
from apps.pedidos.forms import (
    AgregarAlCarritoForm,
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
    QuitarItemForm,
)
from apps.pedidos.models import ItemPedido, Pedido
from apps.pedidos.servicios import (
    TRANSICIONES,
    agregar_item,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").order_by("categoria__nombre", "nombre")
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "catalogo.view_producto"
    model = Producto
    template_name = "catalogo/producto_detail.html"
    context_object_name = "producto"

    def get_queryset(self):
        queryset = Producto.objects.select_related("categoria").prefetch_related(
            Prefetch("opciones", queryset=OpcionProducto.objects.order_by("tipo", "nombre"))
        )
        if self.request.user.has_perm("catalogo.change_producto"):
            return queryset
        return queryset.filter(disponible=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_agregar"] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"], disponible=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Agregar {self.producto.nombre} al carrito"
        context["boton"] = "Agregar al carrito"
        context["cancelar_url"] = reverse_lazy("catalogo:producto_detail", kwargs={"pk": self.producto.pk})
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            agregar_item(
                carrito,
                self.producto,
                form.cleaned_data["cantidad"],
                form.get_opciones(),
            )
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return redirect("pedidos:carrito_detail")


class CarritoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.add_pedido"
    template_name = "pedidos/carrito_detail.html"
    context_object_name = "carrito"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        carrito = self.object
        context["items"] = carrito.items.select_related("producto").prefetch_related("opciones").all()
        context["quitar_form"] = QuitarItemForm()
        context["codigo_form"] = CodigoForm(initial={"codigo": carrito.codigo_descuento.codigo if carrito.codigo_descuento else ""})
        context["confirmar_form"] = ConfirmarPedidoForm(usuario=self.request.user)
        return context


class ItemQuitarView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = QuitarItemForm
    template_name = "pedidos/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(
            ItemPedido.objects.select_related("pedido", "producto"),
            pk=kwargs["pk"],
            pedido__cliente=request.user,
            pedido__estado=Pedido.Estado.CARRITO,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Quitar {self.item.producto.nombre}"
        context["boton"] = "Quitar del carrito"
        context["cancelar_url"] = reverse_lazy("pedidos:carrito_detail")
        return context

    def form_valid(self, form):
        try:
            quitar_item(self.item)
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Producto quitado del carrito.")
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm
    template_name = "pedidos/accion_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Aplicar código de descuento"
        context["boton"] = "Aplicar código"
        context["cancelar_url"] = reverse_lazy("pedidos:carrito_detail")
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(carrito, form.cleaned_data["codigo"])
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Código aplicado correctamente.")
        return redirect("pedidos:carrito_detail")


class CarritoConfirmarView(PermissionRequiredMixin, FormView):
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
        context["boton"] = "Confirmar pedido"
        context["cancelar_url"] = reverse_lazy("pedidos:carrito_detail")
        return context

    def form_valid(self, form):
        carrito = obtener_carrito(self.request.user)
        try:
            confirmar_pedido(
                carrito,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)

        carrito.refresh_from_db()
        if carrito.metodo_pago == Pedido.MetodoPago.TARJETA and hasattr(carrito, "pago"):
            return redirect("pagos:pasarela", referencia=carrito.pago.referencia)
        messages.success(self.request, "Pedido confirmado correctamente.")
        return redirect("pedidos:pedido_detail", pk=carrito.pk)


class PedidoListView(PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.select_related("cliente", "direccion").prefetch_related("items__producto", "items__opciones")
        if user.has_perm("pedidos.add_pedido") and not (user.has_perm("pedidos.preparar_pedido") or user.has_perm("pedidos.despachar_pedido") or user.has_perm("pedidos.ver_reportes") or user.is_staff):
            return qs.filter(cliente=user).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]).order_by("-creado")
        if user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(estado__in=[Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]).order_by("creado")
        if user.has_perm("pedidos.despachar_pedido"):
            return qs.filter(estado__in=[Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]).filter(
                Q(estado=Pedido.Estado.LISTO_DESPACHO) | Q(entrega__repartidor=user)
            ).order_by("-creado")
        if user.has_perm("pedidos.ver_reportes") or user.is_staff:
            return qs.exclude(estado=Pedido.Estado.CARRITO).order_by("-creado")
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["es_cliente"] = user.has_perm("pedidos.add_pedido") and not (user.has_perm("pedidos.preparar_pedido") or user.has_perm("pedidos.despachar_pedido") or user.has_perm("pedidos.ver_reportes") or user.is_staff)
        context["mostrar_cliente"] = not context["es_cliente"]
        return context


class PedidoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.select_related("cliente", "direccion", "codigo_descuento", "pago").prefetch_related(
            "items__producto", "items__opciones", "historial__usuario"
        )
        if user.has_perm("pedidos.add_pedido") and not (user.has_perm("pedidos.preparar_pedido") or user.has_perm("pedidos.despachar_pedido") or user.has_perm("pedidos.ver_reportes") or user.is_staff):
            return qs.filter(cliente=user)
        if user.has_perm("pedidos.preparar_pedido"):
            return qs.filter(estado__in=[Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO])
        if user.has_perm("pedidos.despachar_pedido"):
            return qs.filter(Q(estado__in=[Pedido.Estado.LISTO_DESPACHO]) | Q(entrega__repartidor=user) | Q(cliente=user))
        if user.has_perm("pedidos.ver_reportes") or user.is_staff:
            return qs
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["mostrar_datos_cliente"] = user.has_perm("pedidos.despachar_pedido") or user.is_staff
        context["historial"] = self.object.historial.order_by("fecha")
        estados = []
        for estado in TRANSICIONES.get(self.object.estado, set()):
            if estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO] and user.has_perm("pedidos.preparar_pedido"):
                estados.append((estado, Pedido.Estado(estado).label))
            if estado in [Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO] and user.has_perm("pedidos.despachar_pedido"):
                if estado == Pedido.Estado.ENTREGADO:
                    entrega = getattr(self.object, "entrega", None)
                    if not entrega or entrega.repartidor_id != user.id:
                        continue
                estados.append((estado, Pedido.Estado(estado).label))
        context["puede_cambiar_estado"] = len(estados) > 0
        return context


class PedidoEstadoView(PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm
    template_name = "pedidos/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido.objects.select_related("entrega"), pk=kwargs["pk"])
        estados = self.estados_permitidos(request.user)
        if not estados:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        self.estados = estados
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("pedidos.preparar_pedido") or user.has_perm("pedidos.despachar_pedido")

    def estados_permitidos(self, user):
        estados = []
        for estado in TRANSICIONES.get(self.pedido.estado, set()):
            if estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO] and user.has_perm("pedidos.preparar_pedido"):
                estados.append((estado, Pedido.Estado(estado).label))
            if estado in [Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO] and user.has_perm("pedidos.despachar_pedido"):
                if estado == Pedido.Estado.ENTREGADO:
                    entrega = getattr(self.pedido, "entrega", None)
                    if not entrega or entrega.repartidor_id != user.id:
                        continue
                estados.append((estado, Pedido.Estado(estado).label))
        return estados

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["estados"] = self.estados
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Cambiar estado pedido #{self.pedido.pk}"
        context["boton"] = "Actualizar estado"
        context["cancelar_url"] = reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})
        return context

    def form_valid(self, form):
        try:
            avanzar_pedido(self.pedido, form.cleaned_data["estado"], self.request.user)
        except ValidationError as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Estado del pedido actualizado.")
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)
