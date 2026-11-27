from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    """Resuelve la pasarela simulada y actualiza el pedido. (RF-08, RNF-05)"""
    try:
        pago = Pago.objects.get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("El pago no existe.")
    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("El pago ya fue resuelto.")
    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")
    if pago.pedido.estado != Pedido.Estado.PENDIENTE_PAGO:
        raise ValidationError("El pedido no está pendiente de pago.")

    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.RECIBIDO)
    else:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.CARRITO)
    return pago
