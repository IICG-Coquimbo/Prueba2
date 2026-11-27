"""Logica de negocio de la pasarela de pago simulada."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pagos.models import EstadoPago, MetodoPago, Pago
from apps.pedidos.servicios import registrar_estado


def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: resuelve un pago de tarjeta pendiente y actualiza el pedido."""
    with transaction.atomic():
        try:
            pago = Pago.objects.get(referencia=referencia)
        except Pago.DoesNotExist:
            raise ValidationError("No existe un pago con esa referencia.") from None

        if pago.estado != EstadoPago.PENDIENTE:
            raise ValidationError("El pago ya fue resuelto y no se puede resolver otra vez.")
        if pago.metodo != MetodoPago.TARJETA:
            raise ValidationError("Solo se pueden resolver pagos realizados con tarjeta.")

        if exitoso:
            pago.estado = EstadoPago.EXITOSO
            registrar_estado(pago.pedido, "recibido", None)
        else:
            pago.estado = EstadoPago.FALLIDO
            registrar_estado(pago.pedido, "carrito", None)

        pago.save()
        return pago
