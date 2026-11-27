from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado

from .models import Pago

PENDIENTE = Pago.Estado.PENDIENTE
EXITOSO = Pago.Estado.EXITOSO
FALLIDO = Pago.Estado.FALLIDO


@transaction.atomic
def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("Pago no encontrado.")

    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Este pago no es con tarjeta.")
    if pago.estado != PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto.")

    pedido = pago.pedido
    if exitoso:
        pago.estado = EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pedido, Pedido.Estado.RECIBIDO, usuario=pedido.cliente)
    else:
        pago.estado = FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pedido, Pedido.Estado.CARRITO, usuario=pedido.cliente)
    return pago
