from django.core.exceptions import ValidationError
from django.db import transaction
from apps.pagos.models import Pago
from apps.pedidos.servicios import registrar_estado
from apps.pedidos.models import Pedido


@transaction.atomic
def resultado_pago(referencia, exitoso):
    try:
        pago = Pago.objects.select_related("pedido").get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("Pago no encontrado.")

    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto.")
    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Solo pagos con tarjeta usan la pasarela.")

    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.RECIBIDO)
    else:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=["estado"])
        registrar_estado(pago.pedido, Pedido.Estado.CARRITO)