from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_for_update().get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("Pago no encontrado.")
    if pago.estado != "pendiente":
        raise ValidationError("El pago ya fue resuelto.")
    pedido = pago.pedido
    if exitoso:
        pago.estado = "exitoso"
        from apps.pedidos.servicios import registrar_estado
        registrar_estado(pedido, "recibido")
    else:
        pago.estado = "fallido"
        from apps.pedidos.servicios import registrar_estado
        registrar_estado(pedido, "carrito")
    pago.save()
    return pago
