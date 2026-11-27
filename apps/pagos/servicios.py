from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.servicios import registrar_estado

from .models import Pago


def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: resuelve un pago con tarjeta y actualiza el pedido."""
    with transaction.atomic():
        pago = Pago.objects.filter(referencia=referencia).first()
        if pago is None:
            raise ValidationError('No existe un pago con esa referencia.')
        if pago.estado != 'pendiente':
            raise ValidationError('Este pago ya fue resuelto')
        if pago.metodo != 'tarjeta':
            raise ValidationError('Solo se pueden resolver pagos con tarjeta.')

        if isinstance(exitoso, str):
            valor = exitoso.strip().lower()
            if valor not in ('exitoso', 'fallido', 'true', 'false', '1', '0', 'si', 'no'):
                raise ValidationError('El resultado del pago no es válido.')
            es_exitoso = valor in ('exitoso', 'true', '1', 'si')
        else:
            es_exitoso = bool(exitoso)

        pedido = pago.pedido
        if es_exitoso:
            pago.estado = 'exitoso'
            pago.save(update_fields=['estado'])
            registrar_estado(pedido, 'recibido')
        else:
            pago.estado = 'fallido'
            pago.save(update_fields=['estado'])
            registrar_estado(pedido, 'carrito')
    return pago
