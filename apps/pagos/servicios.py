from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.servicios import registrar_estado

from .models import Pago


def resultado_pago(referencia, exitoso):
    """Resuelve un pago simulado con tarjeta y actualiza el pedido (RF-08, RNF-05)."""
    with transaction.atomic():
        try:
            pago = Pago.objects.select_related("pedido").get(referencia=referencia)
        except Pago.DoesNotExist:
            raise ValidationError("No existe un pago con esa referencia.") from None

        if pago.estado != "pendiente":
            raise ValidationError("El pago ya fue resuelto.")
        if pago.metodo != "tarjeta":
            raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

        if exitoso:
            pago.estado = "exitoso"
            estado_pedido = "recibido"
        else:
            pago.estado = "fallido"
            estado_pedido = "carrito"

        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, estado_pedido)
        return pago
