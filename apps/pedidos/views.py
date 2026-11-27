from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.catalogo.models import OpcionProducto, Producto

from .forms import AgregarAlCarritoForm, CodigoForm, ConfirmarPedidoForm, QuitarItemForm
from .models import ItemPedido, Pedido
from .servicios import agregar_item, aplicar_codigo, confirmar_pedido, obtener_carrito, quitar_item


class PedidosPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    pass


class CarritoDetailView(PedidosPermissionMixin, TemplateView):
    template_name = "pedidos/carrito_detail.html"
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = obtener_carrito(self.request.user)
        context["pedido"] = pedido
        context["items"] = pedido.items.select_related("producto").prefetch_related("opciones").order_by("pk")
        context["codigo_form"] = CodigoForm()
        context["confirmar_form"] = ConfirmarPedidoForm(user=self.request.user)
        return context


class ProductoAgregarView(PedidosPermissionMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = AgregarAlCarritoForm
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        opciones = self._opciones_seleccionadas(form)
        try:
            agregar_item(pedido, self.producto, form.cleaned_data["cantidad"], opciones)
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Producto agregado al carrito.")
        return redirect(self.get_success_url())

    def _opciones_seleccionadas(self, form):
        ids = [form.cleaned_data.get(tipo) for tipo in ["tamano", "leche", "azucar"]]
        ids = [int(valor) for valor in ids if valor]
        return list(OpcionProducto.objects.filter(pk__in=ids))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["producto"] = self.producto
        context["titulo"] = "Agregar al carrito"
        return context


class ItemQuitarView(PedidosPermissionMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = QuitarItemForm
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        item = get_object_or_404(ItemPedido, pk=self.kwargs["pk"], pedido=pedido)
        try:
            quitar_item(item)
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Item quitado del carrito.")
        return redirect(self.get_success_url())


class CarritoCodigoView(PedidosPermissionMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = CodigoForm
    permission_required = "pedidos.add_pedido"
    success_url = reverse_lazy("pedidos:carrito_detail")

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            aplicar_codigo(pedido, form.cleaned_data["texto"])
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error("texto", mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Código aplicado.")
        return redirect(self.get_success_url())


class CarritoConfirmarView(PedidosPermissionMixin, FormView):
    template_name = "pedidos/accion_form.html"
    form_class = ConfirmarPedidoForm
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        try:
            pedido = confirmar_pedido(
                pedido,
                form.cleaned_data["direccion"],
                form.cleaned_data["metodo_pago"],
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Pedido confirmado.")
        if pedido.metodo_pago == Pedido.MetodoPago.TARJETA:
            return redirect(reverse("pagos:pasarela", args=[pedido.pago.referencia]))
        return redirect(reverse("pedidos:pedido_detail", args=[pedido.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Confirmar pedido"
        return context


class PedidoListView(PedidosPermissionMixin, ListView):
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        return Pedido.objects.filter(cliente=self.request.user).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]).order_by("-creado")


class PedidoDetailView(PedidosPermissionMixin, DetailView):
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    permission_required = "pedidos.view_pedido"

    def get_queryset(self):
        return Pedido.objects.filter(cliente=self.request.user).prefetch_related("items__producto", "items__opciones", "historial")
