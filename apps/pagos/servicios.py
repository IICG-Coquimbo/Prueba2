"""Lógica de negocio de pagos (docs/reglas_flujo.md).

La pasarela es simulada: no pide ni guarda números de tarjeta (RNF-03).
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.pedidos.models import EstadoPedido, MetodoPago
from apps.pedidos.servicios import registrar_estado

from .models import EstadoPago, Pago


@transaction.atomic
def resultado_pago(referencia, exitoso):
    """Resuelve la pasarela simulada y actualiza pago y pedido. (RF-08, RNF-05)"""
    pago = Pago.objects.filter(referencia=referencia).first()
    if pago is None:
        raise ValidationError("No existe un pago con esa referencia.")
    if pago.estado != EstadoPago.PENDIENTE:
        raise ValidationError("Este pago ya fue resuelto.")
    if pago.metodo != MetodoPago.TARJETA:
        raise ValidationError("Solo se pueden resolver pagos realizados con tarjeta.")

    if isinstance(exitoso, str):
        if exitoso not in ("exitoso", "fallido"):
            raise ValidationError("El resultado del pago no es válido.")
        exito = exitoso == "exitoso"
    else:
        exito = bool(exitoso)

    pago.estado = EstadoPago.EXITOSO if exito else EstadoPago.FALLIDO
    pago.save(update_fields=["estado"])

    pedido = pago.pedido
    if exito:
        registrar_estado(pedido, EstadoPedido.RECIBIDO)
    else:
        registrar_estado(pedido, EstadoPedido.CARRITO)
    return pago
