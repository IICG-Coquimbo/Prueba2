from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pagos.models import Pago
from apps.pedidos.servicios import registrar_estado


def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: resuelve una sola vez un pago pendiente con tarjeta."""
    pago = Pago.objects.filter(referencia=referencia).first()
    if pago is None:
        raise ValidationError("No existe un pago con esa referencia.")
    if pago.estado != "pendiente":
        raise ValidationError("El pago ya fue resuelto.")
    if pago.metodo != "tarjeta":
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    pedido = pago.pedido
    if pedido.estado != "pendiente_pago":
        raise ValidationError("El pedido no está esperando el pago.")

    with transaction.atomic():
        pago.estado = "exitoso" if exitoso else "fallido"
        pago.save(update_fields=["estado"])
        registrar_estado(pedido, "recibido" if exitoso else "carrito")
    return pago
