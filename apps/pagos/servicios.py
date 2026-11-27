from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pagos.models import EstadoPago, MetodoPago, Pago


@transaction.atomic()
def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05"""
    from apps.pedidos.models import EstadoPedido
    from apps.pedidos.servicios import TRANSICIONES, registrar_estado

    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("No existe un pago con esa referencia.")
    if pago.estado != EstadoPago.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto.")
    if pago.metodo != MetodoPago.TARJETA:
        raise ValidationError("Este pago no se puede resolver en la pasarela.")

    pedido = pago.pedido
    nuevo_estado = EstadoPedido.RECIBIDO if exitoso else EstadoPedido.CARRITO
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError("Transición de estado no permitida.")

    pago.estado = EstadoPago.EXITOSO if exitoso else EstadoPago.FALLIDO
    pago.save(update_fields=["estado"])
    registrar_estado(pedido, nuevo_estado)
    return pago
