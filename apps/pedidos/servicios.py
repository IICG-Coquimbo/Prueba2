import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import OpcionProducto
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido

CARRITO = Pedido.Estado.CARRITO
PENDIENTE_PAGO = Pedido.Estado.PENDIENTE_PAGO
RECIBIDO = Pedido.Estado.RECIBIDO
EN_PREPARACION = Pedido.Estado.EN_PREPARACION
LISTO_DESPACHO = Pedido.Estado.LISTO_DESPACHO
EN_CAMINO = Pedido.Estado.EN_CAMINO
ENTREGADO = Pedido.Estado.ENTREGADO

TRANSICIONES = {
    CARRITO: {RECIBIDO, PENDIENTE_PAGO},
    PENDIENTE_PAGO: {RECIBIDO, CARRITO},
    RECIBIDO: {EN_PREPARACION},
    EN_PREPARACION: {LISTO_DESPACHO},
    LISTO_DESPACHO: {EN_CAMINO},
    EN_CAMINO: {ENTREGADO},
    ENTREGADO: set(),
}

# permiso requerido por transicion
PERMISO_TRANSICION = {
    RECIBIDO: "pedidos.preparar_pedido",
    EN_PREPARACION: "pedidos.preparar_pedido",
    LISTO_DESPACHO: "pedidos.preparar_pedido",
    EN_CAMINO: "pedidos.despachar_pedido",
    ENTREGADO: "pedidos.despachar_pedido",
}


def registrar_estado(pedido, nuevo_estado, usuario=None):
    if nuevo_estado not in Pedido.Estado.values:
        raise ValidationError(f"Estado desconocido: {nuevo_estado}")
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)
    return pedido


def obtener_carrito(usuario):
    # un pedido en carrito por usuario
    carrito = Pedido.objects.filter(cliente=usuario, estado=CARRITO).first()
    if carrito is None:
        carrito = Pedido.objects.create(cliente=usuario, estado=CARRITO)
    return carrito


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones=None):
    opciones = list(opciones or [])
    if pedido.estado != CARRITO:
        raise ValidationError("Solo se puede modificar un pedido en carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no esta disponible.")
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValidationError("La cantidad no es valida.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    # opciones deben pertenecer al producto y maximo una por tipo
    for opcion in opciones:
        if not isinstance(opcion, OpcionProducto) or opcion.producto_id != producto.pk:
            raise ValidationError("Opcion no valida para este producto.")
    tipos = [o.tipo for o in opciones]
    if len(tipos) != len(set(tipos)):
        raise ValidationError("Como maximo una opcion por tipo.")

    precio_unitario = producto.precio + sum(
        (o.recargo for o in opciones), Decimal("0")
    )

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
    if item.pedido.estado != CARRITO:
        raise ValidationError("Solo se puede modificar un pedido en carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def recalcular_totales(pedido):
    subtotal = sum(
        (i.cantidad * i.precio_unitario for i in pedido.items.all()), Decimal("0")
    )
    subtotal = subtotal.quantize(Decimal("0.01"))
    descuento = Decimal("0")
    if pedido.codigo_descuento_id:
        codigo = pedido.codigo_descuento
        descuento = (subtotal * codigo.porcentaje / Decimal("100")).quantize(Decimal("0.01"))
    total = (subtotal - descuento).quantize(Decimal("0.01"))
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    if pedido.estado != CARRITO:
        raise ValidationError("Solo se puede aplicar codigo en un pedido en carrito.")
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto.strip().upper())
    except CodigoDescuento.DoesNotExist:
        codigo = CodigoDescuento.objects.filter(codigo__iexact=texto.strip()).first()
    if codigo is None:
        raise ValidationError("Codigo no encontrado.")
    if not codigo.activo:
        raise ValidationError("El codigo no esta activo.")
    hoy = timezone.localdate()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El codigo no esta vigente.")
    if codigo.solo_primer_pedido:
        otros = Pedido.objects.filter(cliente=pedido.cliente).exclude(pk=pedido.pk).exclude(
            estado__in=[CARRITO, PENDIENTE_PAGO]
        )
        if otros.exists():
            raise ValidationError("El codigo es solo para el primer pedido.")
    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    from apps.pagos.models import Pago

    if pedido.estado != CARRITO:
        raise ValidationError("Solo se puede confirmar un pedido en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El pedido no tiene items.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("Selecciona una direccion valida.")
    if metodo_pago not in (Pedido.MetodoPago.EFECTIVO, Pedido.MetodoPago.TARJETA):
        raise ValidationError("Metodo de pago no valido.")

    recalcular_totales(pedido)
    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])

    Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado="pendiente",
        referencia=str(uuid.uuid4()),
        monto=pedido.total,
    )

    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, RECIBIDO, usuario=pedido.cliente)
    else:
        registrar_estado(pedido, PENDIENTE_PAGO, usuario=pedido.cliente)
    return pedido


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    permitidos = TRANSICIONES.get(pedido.estado, set())
    if nuevo_estado not in permitidos:
        raise ValidationError(
            f"Transicion no permitida: {pedido.estado} -> {nuevo_estado}."
        )

    permiso = PERMISO_TRANSICION.get(nuevo_estado)
    if permiso and usuario is not None and not usuario.has_perm(permiso):
        raise ValidationError("No tienes permiso para esta accion.")

    if nuevo_estado == EN_CAMINO:
        from apps.entregas.models import Entrega

        repartidor = usuario
        Entrega.objects.create(pedido=pedido, repartidor=repartidor, inicio=timezone.now())
    elif nuevo_estado == ENTREGADO:
        from apps.entregas.models import Entrega

        entrega = Entrega.objects.filter(pedido=pedido).first()
        if entrega is None:
            raise ValidationError("El pedido no tiene entrega.")
        if usuario is not None and entrega.repartidor_id != usuario.id:
            raise ValidationError("Solo el repartidor asignado puede marcar entregado.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario=usuario)
    return pedido
