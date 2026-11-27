from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Pago, EstadoPago
from apps.pedidos.servicios import registrar_estado


def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("No se encontr\u00f3 el pago.")
    if pago.estado != EstadoPago.PENDIENTE:
        raise ValidationError(
            "Este pago ya fue resuelto y no se puede modificar."
        )
    if pago.metodo != "tarjeta":
        raise ValidationError(
            "Solo se pueden resolver pagos con tarjeta."
        )
    with transaction.atomic():
        if exitoso:
            pago.estado = EstadoPago.EXITOSO
            registrar_estado(pago.pedido, "recibido")
        else:
            pago.estado = EstadoPago.FALLIDO
            registrar_estado(pago.pedido, "carrito")
        pago.save()
    return pago
