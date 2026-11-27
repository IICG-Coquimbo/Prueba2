from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    """Resuelve un pago pendiente de tarjeta."""
    try:
        pago = Pago.objects.select_for_update().get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("El pago no existe.")

    if pago.estado != "pendiente":
        raise ValidationError("El pago ya fue resuelto previamente.")
    if pago.metodo != "tarjeta":
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    pedido = pago.pedido

    if exitoso:
        pago.estado = "exitoso"
        pago.save()
        from apps.pedidos.servicios import registrar_estado
        registrar_estado(pedido, "recibido")
    else:
        pago.estado = "fallido"
        pago.save()
        from apps.pedidos.servicios import registrar_estado
        registrar_estado(pedido, "carrito")

    return pago
