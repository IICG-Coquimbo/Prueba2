from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cuentas.models import Direccion
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.pedidos.models import HistorialEstado, ItemPedido, Pedido
from apps.promociones.models import CodigoDescuento


TRANSICIONES = {
    Pedido.Estado.CARRITO: {Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO},
    Pedido.Estado.PENDIENTE_PAGO: {Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO},
    Pedido.Estado.RECIBIDO: {Pedido.Estado.EN_PREPARACION},
    Pedido.Estado.EN_PREPARACION: {Pedido.Estado.LISTO_DESPACHO},
    Pedido.Estado.LISTO_DESPACHO: {Pedido.Estado.EN_CAMINO},
    Pedido.Estado.EN_CAMINO: {Pedido.Estado.ENTREGADO},
    Pedido.Estado.ENTREGADO: set(),
}


def obtener_carrito(usuario):
    pedido, _ = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=Pedido.Estado.CARRITO,
        defaults={
            "subtotal": Decimal("0.00"),
            "descuento": Decimal("0.00"),
            "total": Decimal("0.00"),
        },
    )
    return pedido


def recalcular_totales(pedido):
    subtotal = Decimal("0.00")
    for item in pedido.items.all():
        subtotal += item.cantidad * item.precio_unitario
    subtotal = subtotal.quantize(Decimal("0.01"))
    descuento = Decimal("0.00")
    if pedido.codigo_descuento_id:
        porcentaje = Decimal(pedido.codigo_descuento.porcentaje)
        descuento = (subtotal * porcentaje / Decimal("100")).quantize(Decimal("0.01"))
    total = (subtotal - descuento).quantize(Decimal("0.01"))
    if total < Decimal("0.00"):
        total = Decimal("0.00")
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo puedes agregar productos a un carrito activo.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad is None or cantidad < 1:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    opciones = list(opciones)
    tipos_vistos = set()
    for opcion in opciones:
        if opcion.producto_id != producto.id:
            raise ValidationError("La opción seleccionada no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError("Solo puedes elegir una opción por tipo.")
        tipos_vistos.add(opcion.tipo)

    recargo = sum((opcion.recargo for opcion in opciones), Decimal("0.00"))
    precio_unitario = (producto.precio + recargo).quantize(Decimal("0.01"))

    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    if opciones:
        item.opciones.set(opciones)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo puedes quitar productos de un carrito activo.")
    item.delete()
    recalcular_totales(pedido)


@transaction.atomic
def aplicar_codigo(pedido, texto):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo puedes aplicar un código a un carrito activo.")
    codigo = (texto or "").strip().upper()
    try:
        descuento = CodigoDescuento.objects.get(codigo=codigo)
    except CodigoDescuento.DoesNotExist as exc:
        raise ValidationError("El código de descuento no existe.") from exc

    hoy = timezone.localdate()
    if not descuento.activo:
        raise ValidationError("El código de descuento no está activo.")
    if descuento.vigente_desde > hoy or descuento.vigente_hasta < hoy:
        raise ValidationError("El código de descuento no está vigente.")
    if descuento.solo_primer_pedido:
        tiene_pedidos = Pedido.objects.filter(cliente=pedido.cliente).exclude(
            estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
        ).exists()
        if tiene_pedidos:
            raise ValidationError("Este código solo es válido para el primer pedido.")

    pedido.codigo_descuento = descuento
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


def registrar_estado(pedido, nuevo_estado, usuario=None):
    if pedido.estado != nuevo_estado:
        pedido.estado = nuevo_estado
        pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo puedes confirmar un carrito activo.")
    if not pedido.items.exists():
        raise ValidationError("Debes agregar al menos un producto al carrito.")
    if not isinstance(direccion, Direccion) or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección seleccionada no es válida.")
    if metodo_pago not in [Pedido.MetodoPago.EFECTIVO, Pedido.MetodoPago.TARJETA]:
        raise ValidationError("Debes seleccionar una forma de pago válida.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])
    recalcular_totales(pedido)

    pago, _ = Pago.objects.get_or_create(
        pedido=pedido,
        defaults={
            "metodo": metodo_pago,
            "estado": Pago.Estado.PENDIENTE,
            "referencia": str(uuid4()),
            "monto": pedido.total,
        },
    )
    pago.metodo = metodo_pago
    pago.estado = Pago.Estado.PENDIENTE
    pago.monto = pedido.total
    if not pago.referencia:
        pago.referencia = str(uuid4())
    pago.save()

    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO, pedido.cliente)
    else:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO, pedido.cliente)
    return pedido


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    transiciones_validas = TRANSICIONES.get(pedido.estado, set())
    if nuevo_estado not in transiciones_validas:
        raise ValidationError("La transición de estado no es válida.")

    if nuevo_estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif nuevo_estado in [Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
    else:
        raise ValidationError("La transición solicitada no está permitida.")

    if nuevo_estado == Pedido.Estado.EN_CAMINO:
        Entrega.objects.update_or_create(
            pedido=pedido,
            defaults={"repartidor": usuario, "inicio": timezone.now(), "fin": None},
        )
    if nuevo_estado == Pedido.Estado.ENTREGADO:
        entrega = getattr(pedido, "entrega", None)
        if not entrega or entrega.repartidor_id != usuario.id:
            raise ValidationError("Solo el repartidor asignado puede marcar el pedido como entregado.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario)
    return pedido
