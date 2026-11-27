from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.pedidos.forms import CodigoForm, ConfirmarPedidoForm, EstadoPedidoForm
from apps.pedidos.models import EstadoPedido, Pedido
from apps.pedidos.servicios import (
    TRANSICIONES,
    avanzar_pedido,
    aplicar_codigo,
    confirmar_pedido,
    obtener_carrito,
    quitar_item,
)


@login_required
def carrito_detail(request):
    carrito = obtener_carrito(request.user)
    return render(request, "pedidos/carrito_detail.html", {"carrito": carrito})


@login_required
def item_quitar(request, pk):
    carrito = obtener_carrito(request.user)
    item = get_object_or_404(carrito.items.all(), pk=pk)
    if request.method == "POST":
        try:
            quitar_item(item)
        except ValidationError as error:
            from django.contrib import messages
            messages.error(request, error.message)
    return redirect("pedidos:carrito")


@login_required
def carrito_codigo(request):
    carrito = obtener_carrito(request.user)
    if request.method == "POST":
        form = CodigoForm(request.POST)
        if form.is_valid():
            try:
                aplicar_codigo(carrito, form.cleaned_data["codigo"])
                from django.contrib import messages
                messages.success(request, "Codigo de descuento aplicado.")
            except ValidationError as error:
                from django.contrib import messages
                messages.error(request, error.message)
    return redirect("pedidos:carrito")


@login_required
def carrito_confirmar(request):
    carrito = obtener_carrito(request.user)
    from django.contrib import messages
    if request.method == "POST":
        form = ConfirmarPedidoForm(request.user, request.POST)
        if form.is_valid():
            try:
                confirmar_pedido(
                    carrito,
                    form.cleaned_data["direccion"],
                    form.cleaned_data["metodo_pago"],
                )
                messages.success(request, "Pedido confirmado.")
                return redirect("pedidos:pedido_list")
            except ValidationError as error:
                form.add_error(None, error.message)
    else:
        form = ConfirmarPedidoForm(request.user)
    return render(request, "pedidos/carrito_confirmar.html", {"form": form, "carrito": carrito})


@login_required
def pedido_list(request):
    pedidos = Pedido.objects.filter(cliente=request.user).exclude(estado=EstadoPedido.CARRITO).order_by("-creado")
    return render(request, "pedidos/pedido_list.html", {"pedidos": pedidos})


@login_required
def pedido_detail(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    return render(request, "pedidos/pedido_detail.html", {"pedido": pedido})


@login_required
@permission_required("pedidos.preparar_pedido", raise_exception=True)
def pedido_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        form = EstadoPedidoForm(request.POST)
        if form.is_valid():
            try:
                avanzar_pedido(pedido, form.cleaned_data["estado"], request.user)
                messages.success(request, "Estado actualizado.")
                return redirect("pedidos:pedido_detail", pk=pedido.pk)
            except ValidationError as error:
                form.add_error(None, error.message)
    else:
        permitidas = TRANSICIONES.get(pedido.estado, [])
        form = EstadoPedidoForm(estados=permitidas)
    return render(request, "pedidos/pedido_estado.html", {"form": form, "pedido": pedido})
