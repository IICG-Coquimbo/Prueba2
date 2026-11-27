from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Pago


def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: resuelve una vez el pago simulado de tarjeta."""
    pago = Pago.objects.select_related("pedido", "pedido__cliente").filter(referencia=referencia).first()
    if pago is None:
        raise ValidationError("No existe un pago con esa referencia.")
    if pago.metodo != Pago.Metodo.TARJETA or pago.estado != Pago.Estado.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto o no es de tarjeta.")
    if pago.pedido.estado != "pendiente_pago":
        raise ValidationError("El pedido no esta esperando pago.")

    from apps.pedidos.servicios import registrar_estado

    with transaction.atomic():
        pago.estado = Pago.Estado.EXITOSO if exitoso else Pago.Estado.FALLIDO
        pago.save(update_fields=["estado"])
        nuevo_estado = "recibido" if exitoso else "carrito"
        registrar_estado(pago.pedido, nuevo_estado, pago.pedido.cliente)
    return pago
