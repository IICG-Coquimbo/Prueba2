from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado


@transaction.atomic
def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist as exc:
        raise ValidationError("El pago indicado no existe.") from exc

    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")
    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("El pago ya fue resuelto.")

    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.RECIBIDO, pago.pedido.cliente)
    else:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.CARRITO, pago.pedido.cliente)
    return pago
