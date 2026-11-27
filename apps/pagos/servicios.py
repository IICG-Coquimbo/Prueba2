from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    pago = Pago.objects.select_for_update().select_related("pedido").get(referencia=referencia)
    if pago.estado != Pago.Estado.PENDIENTE or pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("El pago no está pendiente de tarjeta.")
    pedido = pago.pedido
    if pedido.estado != Pedido.Estado.PENDIENTE_PAGO:
        raise ValidationError("El pedido no está pendiente de pago.")
    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pedido, Pedido.Estado.RECIBIDO, usuario=pedido.cliente)
    else:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pedido, Pedido.Estado.CARRITO, usuario=pedido.cliente)
    return pago
