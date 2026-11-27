from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Pago, EstadoPago
from apps.pedidos.models import Pedido, EstadoPedido
from apps.pedidos.servicios import registrar_estado as _registrar_estado


def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("Pago no encontrado.")
    if pago.estado != EstadoPago.PENDIENTE:
        raise ValidationError("El pago ya fue resuelto anteriormente.")
    if pago.metodo != "tarjeta":
        raise ValidationError("Solo se puede resolver un pago con tarjeta.")

    with transaction.atomic():
        if exitoso:
            pago.estado = EstadoPago.EXITOSO
            pedido = pago.pedido
            _registrar_estado(pedido, EstadoPedido.RECIBIDO)
        else:
            pago.estado = EstadoPago.FALLIDO
            pedido = pago.pedido
            _registrar_estado(pedido, EstadoPedido.CARRITO)
        pago.save()

    return pago
