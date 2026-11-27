import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido


ESTADOS_CONFIRMADOS = [
    Pedido.Estado.RECIBIDO,
    Pedido.Estado.EN_PREPARACION,
    Pedido.Estado.LISTO_DESPACHO,
    Pedido.Estado.EN_CAMINO,
    Pedido.Estado.ENTREGADO,
]

TRANSICIONES = {
    Pedido.Estado.CARRITO: [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO],
    Pedido.Estado.PENDIENTE_PAGO: [Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO],
    Pedido.Estado.RECIBIDO: [Pedido.Estado.EN_PREPARACION],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.LISTO_DESPACHO],
    Pedido.Estado.LISTO_DESPACHO: [Pedido.Estado.EN_CAMINO],
    Pedido.Estado.EN_CAMINO: [Pedido.Estado.ENTREGADO],
    Pedido.Estado.ENTREGADO: [],
}


def obtener_carrito(usuario):
    pedido, _creado = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=Pedido.Estado.CARRITO,
    )
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden agregar productos al carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    opciones = [op for op in (opciones or []) if op is not None]
    for op in opciones:
        if op.producto_id != producto.pk:
            raise ValidationError("Las opciones deben pertenecer al producto.")
    tipos = [op.tipo for op in opciones]
    if len(tipos) != len(set(tipos)):
        raise ValidationError("Solo se permite una opción por tipo.")

    precio_unitario = producto.precio + sum(
        (op.recargo for op in opciones), Decimal("0.00")
    )
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(opciones)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    if item.pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden quitar productos del carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)


def recalcular_totales(pedido):
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in pedido.items.all()),
        Decimal("0.00"),
    )
    if pedido.codigo_descuento_id:
        descuento = (
            subtotal
            * Decimal(pedido.codigo_descuento.porcentaje)
            / Decimal(100)
        )
    else:
        descuento = Decimal("0.00")
    total = subtotal - descuento

    pedido.subtotal = subtotal.quantize(Decimal("0.01"))
    pedido.descuento = descuento.quantize(Decimal("0.01"))
    pedido.total = total.quantize(Decimal("0.01"))
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    texto = texto.strip().upper()
    if not texto:
        raise ValidationError("Ingresa un código de descuento.")
    codigo = CodigoDescuento.objects.filter(codigo__iexact=texto).first()
    if codigo is None:
        raise ValidationError("El código de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")
    hoy = timezone.localdate()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código de descuento no está vigente.")
    if codigo.solo_primer_pedido and pedido.cliente.pedidos.exclude(
        estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
    ).exists():
        raise ValidationError("Este código solo vale para el primer pedido.")

    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede confirmar un pedido en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito está vacío.")
    if direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección no pertenece al cliente.")
    if metodo_pago not in Pedido.MetodoPago.values:
        raise ValidationError("El método de pago no es válido.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])
    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=Pago.Estado.PENDIENTE,
        referencia=str(uuid.uuid4()),
        monto=pedido.total,
    )
    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO)
    else:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO)
    return pago


@transaction.atomic
def registrar_estado(pedido, nuevo_estado, usuario=None):
    try:
        nuevo_estado = Pedido.Estado(nuevo_estado)
    except ValueError:
        raise ValidationError("El estado del pedido no es válido.") from None
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(
        pedido=pedido,
        estado=nuevo_estado,
        usuario=usuario,
    )
    return pedido


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    try:
        nuevo_estado = Pedido.Estado(nuevo_estado)
    except ValueError:
        raise ValidationError("El estado del pedido no es válido.") from None
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError("Transición de estado no permitida.")

    if nuevo_estado in (
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
    ):
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError(
                "No tienes permiso para realizar este cambio de estado."
            )
    elif nuevo_estado in (Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO):
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError(
                "No tienes permiso para realizar este cambio de estado."
            )

    if (
        pedido.estado == Pedido.Estado.LISTO_DESPACHO
        and nuevo_estado == Pedido.Estado.EN_CAMINO
    ):
        Entrega.objects.create(
            pedido=pedido,
            repartidor=usuario,
            inicio=timezone.now(),
        )
    elif (
        pedido.estado == Pedido.Estado.EN_CAMINO
        and nuevo_estado == Pedido.Estado.ENTREGADO
    ):
        if pedido.entrega.repartidor_id != usuario.pk:
            raise ValidationError(
                "Solo el repartidor asignado puede entregar este pedido."
            )
        pedido.entrega.fin = timezone.now()
        pedido.entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


def ventas_periodo(dias):
    inicio = timezone.localdate() - timedelta(days=dias - 1)
    total = Pedido.objects.filter(
        estado__in=ESTADOS_CONFIRMADOS,
        creado__date__gte=inicio,
    ).aggregate(total=Sum("total"))["total"]
    if total is None:
        return Decimal("0.00")
    return total.quantize(Decimal("0.01"))


def productos_mas_pedidos(limite=5):
    return (
        Producto.objects.filter(items__pedido__estado__in=ESTADOS_CONFIRMADOS)
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades")[:limite]
    )


def ranking_repartidores():
    filas = []
    for usuario in User.objects.filter(entregas__fin__isnull=False).distinct():
        entregas = usuario.entregas.filter(fin__isnull=False)
        total = entregas.count()
        minutos = [
            entrega.minutos
            for entrega in entregas
            if entrega.minutos is not None
        ]
        promedio = sum(minutos) / total if total else 0
        filas.append(
            {
                "repartidor": usuario,
                "entregas": total,
                "minutos_promedio": round(promedio, 2),
            }
        )
    filas.sort(key=lambda fila: fila["entregas"], reverse=True)
    return filas
