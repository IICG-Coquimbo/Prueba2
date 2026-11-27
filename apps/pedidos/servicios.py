from django.db import transaction
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DurationField
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
import uuid

from .models import (
    Pedido, ItemPedido, HistorialEstado,
    ESTADO_CARRITO, ESTADO_PENDIENTE_PAGO, ESTADO_RECIBIDO,
    ESTADO_EN_PREPARACION, ESTADO_LISTO_DESPACHO, ESTADO_EN_CAMINO, ESTADO_ENTREGADO,
    METODO_EFECTIVO, METODO_TARJETA,
)
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pagos.models import Pago
from apps.entregas.models import Entrega


TRANSICIONES = {
    ESTADO_CARRITO: [
        ESTADO_RECIBIDO,
        ESTADO_PENDIENTE_PAGO,
    ],
    ESTADO_PENDIENTE_PAGO: [
        ESTADO_RECIBIDO,
        ESTADO_CARRITO,
    ],
    ESTADO_RECIBIDO: [
        ESTADO_EN_PREPARACION,
    ],
    ESTADO_EN_PREPARACION: [
        ESTADO_LISTO_DESPACHO,
    ],
    ESTADO_LISTO_DESPACHO: [
        ESTADO_EN_CAMINO,
    ],
    ESTADO_EN_CAMINO: [
        ESTADO_ENTREGADO,
    ],
    ESTADO_ENTREGADO: [],
}


def obtener_carrito(usuario):
    pedido, creado = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=ESTADO_CARRITO,
    )
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != ESTADO_CARRITO:
        raise ValidationError("Solo se puede agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no esta disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    tipos_vistos = set()
    for opcion in opciones:
        if opcion.producto_id != producto.id:
            raise ValidationError("La opcion no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError("Solo se permite una opcion por tipo.")
        tipos_vistos.add(opcion.tipo)

    recargo_total = sum((o.recargo for o in opciones), 0)
    precio_unitario = producto.precio + recargo_total

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
    if item.pedido.estado != ESTADO_CARRITO:
        raise ValidationError("Solo se puede quitar items de un carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)


def recalcular_totales(pedido):
    items = pedido.items.all()
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in items),
        0,
    )
    descuento = 0
    if pedido.codigo_descuento_id:
        descuento = subtotal * pedido.codigo_descuento.porcentaje / 100
    total = subtotal - descuento
    pedido.subtotal = round(subtotal, 2)
    pedido.descuento = round(descuento, 2)
    pedido.total = round(total, 2)
    pedido.save(update_fields=["subtotal", "descuento", "total"])


@transaction.atomic
def aplicar_codigo(pedido, texto):
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El codigo de descuento no existe.")

    if not codigo.activo:
        raise ValidationError("El codigo de descuento no esta activo.")

    hoy = date.today()
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El codigo de descuento no esta vigente.")

    if codigo.solo_primer_pedido:
        tiene_otros = Pedido.objects.filter(
            cliente=pedido.cliente,
        ).exclude(
            estado__in=[ESTADO_CARRITO, ESTADO_PENDIENTE_PAGO],
        ).exists()
        if tiene_otros:
            raise ValidationError("Este codigo es solo para el primer pedido.")

    pedido.codigo_descuento = codigo
    recalcular_totales(pedido)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != ESTADO_CARRITO:
        raise ValidationError("Solo se puede confirmar un carrito.")
    if pedido.items.count() == 0:
        raise ValidationError("El carrito no tiene items.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La direccion no pertenece al cliente.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago

    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=Pago.ESTADO_PENDIENTE,
        referencia=str(uuid.uuid4()),
        monto=pedido.total,
    )

    if metodo_pago == METODO_EFECTIVO:
        registrar_estado(pedido, ESTADO_RECIBIDO)
    else:
        registrar_estado(pedido, ESTADO_PENDIENTE_PAGO)

    return pago


def registrar_estado(pedido, nuevo_estado, usuario=None):
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(
        pedido=pedido,
        estado=nuevo_estado,
        usuario=usuario,
    )


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    estado_anterior = pedido.estado
    estados_permitidos = TRANSICIONES.get(pedido.estado, [])
    if nuevo_estado not in estados_permitidos:
        raise ValidationError("Transicion de estado no permitida.")

    if estado_anterior in [
        ESTADO_RECIBIDO,
        ESTADO_EN_PREPARACION,
    ]:
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tiene permiso para preparar pedidos.")

    if estado_anterior == ESTADO_LISTO_DESPACHO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar pedidos.")

    if estado_anterior == ESTADO_EN_CAMINO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar pedidos.")
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("No hay entrega asignada para este pedido.")
        if entrega.repartidor_id != usuario.id:
            raise ValidationError("Solo el repartidor de la entrega puede marcarla como entregada.")

    registrar_estado(pedido, nuevo_estado, usuario=usuario)

    if estado_anterior == ESTADO_LISTO_DESPACHO and nuevo_estado == ESTADO_EN_CAMINO:
        Entrega.objects.create(
            pedido=pedido,
            repartidor=usuario,
            inicio=timezone.now(),
        )

    if estado_anterior == ESTADO_EN_CAMINO and nuevo_estado == ESTADO_ENTREGADO:
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("No hay entrega asignada para este pedido.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    return pedido


def ventas_periodo(dias):
    fecha_limite = timezone.now() - timedelta(days=dias - 1)
    fecha_limite = fecha_limite.replace(hour=0, minute=0, second=0, microsecond=0)
    estados_validos = [
        ESTADO_RECIBIDO,
        ESTADO_EN_PREPARACION,
        ESTADO_LISTO_DESPACHO,
        ESTADO_EN_CAMINO,
        ESTADO_ENTREGADO,
    ]
    total = (
        Pedido.objects.filter(
            estado__in=estados_validos,
            creado__gte=fecha_limite,
        ).aggregate(suma=Sum("total"))["suma"]
        or 0
    )
    return round(total, 2)


def productos_mas_pedidos(limite=5):
    estados_validos = [
        ESTADO_RECIBIDO,
        ESTADO_EN_PREPARACION,
        ESTADO_LISTO_DESPACHO,
        ESTADO_EN_CAMINO,
        ESTADO_ENTREGADO,
    ]
    return (
        Producto.objects.filter(
            items__pedido__estado__in=estados_validos,
        )
        .annotate(total_unidades=Sum("items__cantidad"))
        .filter(total_unidades__gt=0)
        .order_by("-total_unidades")[:limite]
    )


def ranking_repartidores():
    entregas = (
        Entrega.objects.filter(fin__isnull=False)
        .annotate(
            duracion=ExpressionWrapper(
                F("fin") - F("inicio"),
                output_field=DurationField(),
            )
        )
    )

    datos = {}
    for entrega in entregas:
        rid = entrega.repartidor_id
        if rid not in datos:
            datos[rid] = {"repartidor": entrega.repartidor, "entregas": 0, "minutos_total": 0}
        datos[rid]["entregas"] += 1
        datos[rid]["minutos_total"] += int(entrega.duracion.total_seconds() // 60)

    ranking = []
    for rid, info in datos.items():
        promedio = round(info["minutos_total"] / info["entregas"]) if info["entregas"] else 0
        ranking.append({
            "repartidor": info["repartidor"],
            "entregas": info["entregas"],
            "minutos_promedio": promedio,
        })

    ranking.sort(key=lambda x: x["entregas"], reverse=True)
    return ranking
