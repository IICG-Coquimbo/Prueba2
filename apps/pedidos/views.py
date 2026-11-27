from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView, View

from .forms import (
    AgregarAlCarritoForm,
    CodigoForm,
    ConfirmarPedidoForm,
    EstadoPedidoForm,
)
from .models import ItemPedido, Pedido
from .servicios import (
    agregar_item,
    aplicar_codigo,
    avanzar_pedido,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
    registrar_estado,
)
from apps.catalogo.models import Producto


class CarritoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.add_pedido"
    model = Pedido
    template_name = "pedidos/carrito_detail.html"
    context_object_name = "pedido"

    def get_object(self, queryset=None):
        return obtener_carrito(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["codigo_form"] = CodigoForm()
        ctx["confirmar_form"] = ConfirmarPedidoForm(usuario=self.request.user)
        return ctx


class ItemQuitarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pedidos.add_pedido"

    def get(self, request, *args, **kwargs):
        item = get_object_or_404(ItemPedido, pk=self.kwargs["pk"])
        if item.pedido.cliente != self.request.user:
            raise PermissionDenied
        quitar_item(item)
        return redirect("pedidos:carrito_detail")


class CarritoCodigoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pedidos.add_pedido"
    form_class = CodigoForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        pedido = obtener_carrito(request.user)
        if form.is_valid():
            try:
                aplicar_codigo(pedido, form.cleaned_data["codigo"])
            except ValidationError as e:
                messages.error(request, e.messages[0])
                return redirect("pedidos:carrito_detail")
            return redirect("pedidos:carrito_detail")
        messages.error(request, "Codigo invalido")
        return redirect("pedidos:carrito_detail")


class CarritoConfirmarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "pedidos.add_pedido"
    form_class = ConfirmarPedidoForm

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, usuario=request.user)
        pedido = obtener_carrito(request.user)
        if form.is_valid():
            try:
                confirmar_pedido(
                    pedido,
                    form.cleaned_data["direccion"],
                    form.cleaned_data["metodo_pago"],
                )
            except ValidationError as e:
                messages.error(request, e.messages[0])
                return redirect("pedidos:carrito_detail")
            return redirect("pedidos:pedido_detail", pk=pedido.pk)
        messages.error(request, "Datos invalidos")
        return redirect("pedidos:carrito_detail")


class PedidoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_list.html"
    context_object_name = "pedidos"

    def get_queryset(self):
        user = self.request.user
        qs = Pedido.objects.exclude(estado="carrito")
        if user.groups.filter(name="Cliente").exists():
            qs = qs.filter(cliente=user).exclude(estado="pendiente_pago")
        elif user.groups.filter(name="Barista").exists():
            qs = qs.filter(estado__in=["recibido", "en_preparacion", "listo_despacho"])
        elif user.groups.filter(name="Repartidor").exists():
            qs = qs.filter(estado="listo_despacho") | qs.filter(
                estado__in=["en_camino", "entregado"], entrega__repartidor=user
            )
        return qs.order_by("creado")


class PedidoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "pedidos.view_pedido"
    model = Pedido
    template_name = "pedidos/pedido_detail.html"
    context_object_name = "pedido"


class PedidoEstadoView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = EstadoPedidoForm

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, pk=kwargs["pk"])
        user = request.user
        if user.groups.filter(name="Barista").exists():
            self.permission_required = "pedidos.preparar_pedido"
        elif user.groups.filter(name="Repartidor").exists():
            self.permission_required = "pedidos.despachar_pedido"
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def check_permissions(self, request):
        pass

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        estados_siguientes = []
        user = self.request.user
        actual = self.pedido.estado
        if user.groups.filter(name="Barista").exists():
            if actual == "recibido":
                estados_siguientes = ["en_preparacion"]
            elif actual == "en_preparacion":
                estados_siguientes = ["listo_despacho"]
        elif user.groups.filter(name="Repartidor").exists():
            if actual == "listo_despacho":
                estados_siguientes = ["en_camino"]
            elif actual == "en_camino":
                try:
                    if self.pedido.entrega.repartidor == user:
                        estados_siguientes = ["entregado"]
                except Exception:
                    estados_siguientes = []
        kwargs["estados"] = estados_siguientes
        return kwargs

    def form_valid(self, form):
        nuevo_estado = form.cleaned_data["estado"]
        try:
            avanzar_pedido(self.pedido, nuevo_estado, self.request.user)
        except ValidationError as e:
            form.add_error(None, e.messages[0])
            return self.form_invalid(form)
        return redirect("pedidos:pedido_detail", pk=self.pedido.pk)

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})


class ProductoAgregarView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = AgregarAlCarritoForm
    template_name = "catalogo/producto_agregar.html"

    def dispatch(self, request, *args, **kwargs):
        self.producto = get_object_or_404(Producto, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["producto"] = self.producto
        return ctx

    def form_valid(self, form):
        pedido = obtener_carrito(self.request.user)
        opciones = []
        for tipo in ("tamano", "leche", "azucar"):
            campo = f"opcion_{tipo}"
            if campo in form.cleaned_data and form.cleaned_data[campo]:
                opciones.append(form.cleaned_data[campo])
        try:
            agregar_item(
                pedido,
                self.producto,
                form.cleaned_data["cantidad"],
                opciones,
            )
        except ValidationError as e:
            form.add_error(None, e.messages[0])
            return self.form_invalid(form)
        return redirect("pedidos:carrito_detail")

