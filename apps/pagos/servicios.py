from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.pedidos.servicios import registrar_estado


@transaction.atomic
def resultado_pago(referencia, exitoso):
    """
    RF-08, RNF-05: Procesa el resultado de la pasarela de pago simulada.
    Valida: pago pendiente, método tarjeta, no resuelto previamente.
    Exitoso: pago exitoso + pedido recibido.
    Fallido: pago fallido + pedido vuelve a carrito.
    """
    try:
        pago = Pago.objects.select_related('pedido').get(referencia=referencia)
    except Pago.DoesNotExist:
        raise ValidationError("El pago no existe.")

    if pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("El pago ya ha sido resuelto.")

    if pago.metodo != Pago.Metodo.TARJETA:
        raise ValidationError("Este pago no corresponde a una transacción con tarjeta.")

    pedido = pago.pedido

    if exitoso:
        pago.estado = Pago.Estado.EXITOSO
        pago.save(update_fields=['estado'])
        registrar_estado(pedido, Pedido.Estado.RECIBIDO)
    else:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=['estado'])
        registrar_estado(pedido, Pedido.Estado.CARRITO)