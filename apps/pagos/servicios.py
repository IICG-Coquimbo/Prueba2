from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Pago
from apps.pedidos.servicios import registrar_estado


@transaction.atomic
def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("No se encontro el pago con esa referencia.")

    if pago.estado != Pago.ESTADO_PENDIENTE:
        raise ValidationError("El pago ya fue resuelto previamente.")

    if pago.metodo != "tarjeta":
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    if exitoso:
        pago.estado = Pago.ESTADO_EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, "recibido")
    else:
        pago.estado = Pago.ESTADO_FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, "carrito")

    return pago
