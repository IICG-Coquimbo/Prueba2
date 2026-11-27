from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    pago = Pago.objects.filter(referencia=referencia).first()
    if pago is None:
        raise ValidationError("No existe un pago con esa referencia.")
    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto.")
    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        registrar_estado(pago.pedido, Pedido.Estado.RECIBIDO, None)
    else:
        pago.estado = Pago.Estado.FALLIDO
        registrar_estado(pago.pedido, Pedido.Estado.CARRITO, None)
    pago.save(update_fields=["estado"])
    return pago
