from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.entregas.models import Entrega
from apps.pedidos.models import (
    EstadoPedido,
    HistorialEstado,
    ItemPedido,
    MetodoPago,
    Pedido,
)
from apps.promociones.models import CodigoDescuento

TRANSICIONES = {
    EstadoPedido.CARRITO: [EstadoPedido.PENDIENTE_PAGO, EstadoPedido.RECIBIDO],
    EstadoPedido.PENDIENTE_PAGO: [EstadoPedido.RECIBIDO, EstadoPedido.CARRITO],
    EstadoPedido.RECIBIDO: [EstadoPedido.EN_PREPARACION],
    EstadoPedido.EN_PREPARACION: [EstadoPedido.LISTO_DESPACHO],
    EstadoPedido.LISTO_DESPACHO: [EstadoPedido.EN_CAMINO],
    EstadoPedido.EN_CAMINO: [EstadoPedido.ENTREGADO],
    EstadoPedido.ENTREGADO: [],
}

ESTADOS_VENDIDOS = [
    EstadoPedido.RECIBIDO,
    EstadoPedido.EN_PREPARACION,
    EstadoPedido.LISTO_DESPACHO,
    EstadoPedido.EN_CAMINO,
    EstadoPedido.ENTREGADO,
]


def _dinero(valor):
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def obtener_carrito(usuario):
    """RF-04"""
    pedido, _creado = Pedido.objects.get_or_create(
        cliente=usuario, estado=EstadoPedido.CARRITO
    )
    return pedido


@transaction.atomic()
def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15"""
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    seleccionadas = []
    tipos = set()
    recargos = Decimal("0")
    for opcion in opciones:
        if opcion is None:
            continue
        if opcion.producto_id != producto.pk:
            raise ValidationError("Las opciones deben pertenecer al producto.")
        if opcion.tipo in tipos:
            raise ValidationError("Solo se permite una opción por tipo.")
        tipos.add(opcion.tipo)
        seleccionadas.append(opcion)
        recargos += Decimal(str(opcion.recargo))

    precio_unitario = (_dinero(producto.precio) + recargos).quantize(Decimal("0.01"))
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    if seleccionadas:
        item.opciones.set(seleccionadas)
    recalcular_totales(pedido)
    return item


@transaction.atomic()
def quitar_item(item):
    """RF-04"""
    pedido = item.pedido
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    item.delete()
    return recalcular_totales(pedido)


@transaction.atomic()
def recalcular_totales(pedido):
    """RF-04, RF-05"""
    subtotal = sum(
        (
            Decimal(str(item.cantidad)) * Decimal(str(item.precio_unitario))
            for item in pedido.items.all()
        ),
        Decimal("0"),
    ).quantize(Decimal("0.01"))
    if pedido.codigo_descuento_id:
        descuento = (
            subtotal
            * Decimal(pedido.codigo_descuento.porcentaje)
            / Decimal("100")
        ).quantize(Decimal("0.01"))
    else:
        descuento = Decimal("0.00")
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = (subtotal - descuento).quantize(Decimal("0.01"))
    pedido.save()
    return pedido


@transaction.atomic()
def aplicar_codigo(pedido, texto):
    """RF-16"""
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El código de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")
    hoy = timezone.localdate()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código de descuento no está vigente.")
    if codigo.solo_primer_pedido:
        tiene_pedidos = (
            Pedido.objects.filter(cliente=pedido.cliente)
            .exclude(estado__in=[EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO])
            .exists()
        )
        if tiene_pedidos:
            raise ValidationError(
                "El código de descuento solo vale para el primer pedido."
            )
    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    return recalcular_totales(pedido)


@transaction.atomic()
def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07"""
    from apps.pagos.models import EstadoPago, Pago

    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El pedido no tiene productos.")
    if direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección no pertenece al cliente.")
    if metodo_pago not in MetodoPago.values:
        raise ValidationError("El método de pago no es válido.")

    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=EstadoPago.PENDIENTE,
        referencia=str(uuid4()),
        monto=_dinero(pedido.total),
    )
    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    if metodo_pago == MetodoPago.EFECTIVO:
        registrar_estado(pedido, EstadoPedido.RECIBIDO)
    else:
        registrar_estado(pedido, EstadoPedido.PENDIENTE_PAGO)
    return pago


@transaction.atomic()
def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14"""
    estado_actual = pedido.estado
    if nuevo_estado not in TRANSICIONES.get(estado_actual, []):
        raise ValidationError("Transición de estado no permitida.")

    if estado_actual in (EstadoPedido.RECIBIDO, EstadoPedido.EN_PREPARACION):
        if usuario is None or not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar el pedido.")
    elif estado_actual in (EstadoPedido.LISTO_DESPACHO, EstadoPedido.EN_CAMINO):
        if usuario is None or not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar el pedido.")

    if (
        estado_actual == EstadoPedido.LISTO_DESPACHO
        and nuevo_estado == EstadoPedido.EN_CAMINO
    ):
        try:
            pedido.entrega
        except Entrega.DoesNotExist:
            pass
        else:
            raise ValidationError("El pedido ya tiene una entrega.")
        Entrega.objects.create(
            pedido=pedido, repartidor=usuario, inicio=timezone.now()
        )
    elif (
        estado_actual == EstadoPedido.EN_CAMINO
        and nuevo_estado == EstadoPedido.ENTREGADO
    ):
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("El pedido no tiene una entrega.")
        if entrega.repartidor_id != usuario.pk:
            raise ValidationError(
                "Solo el repartidor de la entrega puede entregar el pedido."
            )
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


@transaction.atomic()
def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RNF-07"""
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError("Transición de estado no permitida.")
    pedido.estado = nuevo_estado
    pedido.save()
    return HistorialEstado.objects.create(
        pedido=pedido, estado=nuevo_estado, usuario=usuario
    )


@transaction.atomic()
def ventas_periodo(dias):
    """RF-17"""
    desde = timezone.localdate() - timedelta(days=dias - 1)
    total = (
        Pedido.objects.filter(estado__in=ESTADOS_VENDIDOS, creado__date__gte=desde)
        .aggregate(total=Sum("total"))
        .get("total")
    )
    if total is None:
        return Decimal("0.00")
    return _dinero(total)


@transaction.atomic()
def productos_mas_pedidos(limite=5):
    """RF-17"""
    filas = (
        ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENDIDOS)
        .values("producto")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades", "producto")[:limite]
    )
    productos = Producto.objects.in_bulk([fila["producto"] for fila in filas])
    return [
        {"producto": productos[fila["producto"]], "unidades": fila["unidades"]}
        for fila in filas
    ]


@transaction.atomic()
def ranking_repartidores():
    """RF-18"""
    agrupados = {}
    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    for entrega in entregas:
        datos = agrupados.setdefault(
            entrega.repartidor_id,
            {"repartidor": entrega.repartidor, "entregas": 0, "minutos": 0},
        )
        datos["entregas"] += 1
        datos["minutos"] += entrega.minutos or 0

    resultado = []
    for datos in agrupados.values():
        promedio = (
            Decimal(datos["minutos"]) / Decimal(datos["entregas"])
        ).quantize(Decimal("0.01"))
        resultado.append(
            {
                "repartidor": datos["repartidor"],
                "entregas": datos["entregas"],
                "promedio_minutos": promedio,
            }
        )
    return sorted(
        resultado, key=lambda fila: (-fila["entregas"], fila["repartidor"].pk)
    )
