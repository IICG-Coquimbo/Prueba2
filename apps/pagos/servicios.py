from django.db import transaction
from django.core.exceptions import ValidationError

from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado


def resultado_pago(referencia, exitoso):
    """Exige Pago pendiente de metodo tarjeta.
    Exitoso: pago exitoso y pedido recibido.
    Fallido: pago fallido y pedido de vuelta a carrito.
    Un pago ya resuelto no se puede resolver otra vez. (RF-08, RNF-05)"""
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("No se encontro el pago.")
    if pago.estado != Pago.EstadoPago.PENDIENTE:
        raise ValidationError("El pago ya fue resuelto.")
    if pago.metodo != Pago.MetodoPago.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos con tarjeta.")

    with transaction.atomic():
        if exitoso:
            pago.estado = Pago.EstadoPago.EXITOSO
            pago.save()
            registrar_estado(pago.pedido, Pedido.EstadoPedido.RECIBIDO)
        else:
            pago.estado = Pago.EstadoPago.FALLIDO
            pago.save()
            registrar_estado(pago.pedido, Pedido.EstadoPedido.CARRITO)
    return pago
