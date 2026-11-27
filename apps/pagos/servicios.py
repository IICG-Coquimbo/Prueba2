import importlib
import sys

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from pagos.models import Pago


def _get_registrar_estado():
    """Importo lazy para evitar circular imports con pedidos.servicios."""
    if "pedidos.servicios" in sys.modules:
        from pedidos.servicios import registrar_estado
        return registrar_estado
    # Importo dinámico si aún no está cargado
    return importlib.import_module("pedidos.servicios").registrar_estado


def resultado_pago(referencia, exitoso):
    """RF-08, RNF-05: exige Pago pendiente de metodo tarjeta.
    Exitoso: pago exitoso y pedido recibido.
    Fallido: pago fallido y pedido de vuelta a carrito.
    Un pago ya resuelto no se puede resolver otra vez."""
    try:
        pago = Pago.objects.get(referencia=referencia, estado="pendiente")
    except Pago.DoesNotExist:
        raise ValidationError("El pago no existe o ya ha sido resuelto.")

    if pago.estado != "pendiente":
        raise ValidationError("Este pago ya ha sido resuelto anteriormente.")

    with transaction.atomic():
        if exitoso:
            pago.estado = "exitoso"
            pago.save()
            # El pedido pasa a estado recibido
            pedido = pago.pedido
            registrar_estado = _get_registrar_estado()
            registrar_estado(pedido, "recibido", usuario=pedido.cliente)
        else:
            pago.estado = "fallido"
            pago.save()
            # El pedido vuelve a carrito
            pedido = pago.pedido
            pedido.estado = "carrito"
            pedido.save(update_fields=["estado"])
            # Limpiar codigo_descuento al volver a carrito
            pedido.codigo_descuento = None
            pedido.save(update_fields=["codigo_descuento"])

    return pago