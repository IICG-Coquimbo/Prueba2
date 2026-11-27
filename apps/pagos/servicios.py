from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: resuelve el intento simulado y devuelve su pedido."""
    if type(exitoso) is not bool:
        raise ValidationError("Selecciona un resultado válido para el pago simulado.")

    pedido_id = Pago.objects.filter(referencia=referencia).values_list("pedido_id", flat=True).first()
    if pedido_id is None:
        raise ValidationError("La referencia de pago no existe o ya no está vigente.")

    # Mismo orden de bloqueo que al confirmar: primero el pedido, luego el pago.
    pedido = Pedido.objects.select_for_update(no_key=True).filter(pk=pedido_id).first()
    pago = Pago.objects.select_for_update().filter(pedido_id=pedido_id, referencia=referencia).first()
    if pedido is None or pago is None:
        raise ValidationError("La referencia de pago no existe o ya no está vigente.")
    if (
        pago.metodo != Pedido.MetodoPago.TARJETA
        or pago.estado != Pago.Estado.PENDIENTE
        or pedido.estado != Pedido.Estado.PENDIENTE_PAGO
    ):
        raise ValidationError("El pedido no tiene un pago con tarjeta pendiente de resolución.")

    pago.estado = Pago.Estado.EXITOSO if exitoso else Pago.Estado.FALLIDO
    pago.save(update_fields=["estado"])
    siguiente = Pedido.Estado.RECIBIDO if exitoso else Pedido.Estado.CARRITO
    registrar_estado(pedido, siguiente)
    return pedido
