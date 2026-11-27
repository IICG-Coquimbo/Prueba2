"""Servicios de la app pagos segun docs/reglas_flujo.md."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Pago


def resultado_pago(referencia, exitoso):
    """Resuelve un pago pendiente de metodo tarjeta.

    Exitoso: pago exitoso y pedido recibido.
    Fallido: pago fallido y pedido de vuelta a carrito.
    Un pago ya resuelto no se puede resolver otra vez.
    """
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("No se encontro el pago con esa referencia.")

    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto previamente.")

    pedido = pago.pedido

    with transaction.atomic():
        if exitoso:
            pago.estado = Pago.Estado.EXITOSO
            pago.fecha = timezone.now()
            pago.save()
            from apps.pedidos.servicios import registrar_estado

            registrar_estado(pedido, pedido.Estado.RECIBIDO)
        else:
            pago.estado = Pago.Estado.FALLIDO
            pago.fecha = timezone.now()
            pago.save()
            from apps.pedidos.servicios import registrar_estado

            registrar_estado(pedido, pedido.Estado.CARRITO)

    return pago
