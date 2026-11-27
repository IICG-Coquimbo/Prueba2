import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Pedido, ItemPedido, HistorialEstado, EstadoPedido
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pagos.models import Pago, EstadoPago, MetodoPago
from apps.entregas.models import Entrega


TRANSICIONES = {
    EstadoPedido.CARRITO: [
        EstadoPedido.RECIBIDO,
        EstadoPedido.PENDIENTE_PAGO,
    ],
    EstadoPedido.PENDIENTE_PAGO: [
        EstadoPedido.RECIBIDO,
        EstadoPedido.CARRITO,
    ],
    EstadoPedido.RECIBIDO: [
        EstadoPedido.EN_PREPARACION,
    ],
    EstadoPedido.EN_PREPARACION: [
        EstadoPedido.LISTO_DESPACHO,
    ],
    EstadoPedido.LISTO_DESPACHO: [
        EstadoPedido.EN_CAMINO,
    ],
    EstadoPedido.EN_CAMINO: [
        EstadoPedido.ENTREGADO,
    ],
    EstadoPedido.ENTREGADO: [],
}


def obtener_carrito(usuario):
    pedido = Pedido.objects.filter(
        cliente=usuario, estado=EstadoPedido.CARRITO
    ).first()
    if not pedido:
        pedido = Pedido.objects.create(cliente=usuario, estado=EstadoPedido.CARRITO)
    return pedido


def recalcular_totales(pedido):
    items = pedido.items.all()
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in items), Decimal("0")
    )
    descuento = Decimal("0")
    if pedido.codigo_descuento_id:
        descuento = (subtotal * pedido.codigo_descuento.porcentaje) / Decimal(100)
    descuento = descuento.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal - descuento).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    pedido.subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    pedido.descuento = descuento
    pedido.total = total
    pedido.save()


def registrar_estado(pedido, nuevo_estado, usuario=None):
    if pedido.estado == nuevo_estado:
        raise ValidationError("El pedido ya esta en ese estado.")
    pedido.estado = nuevo_estado
    pedido.save()
    HistorialEstado.objects.create(
        pedido=pedido, estado=nuevo_estado, usuario=usuario
    )


def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no esta disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")
    if opciones:
        tipos_usados = set()
        for op in opciones:
            if op.producto_id != producto.id:
                raise ValidationError(
                    "La opcion no pertenece a este producto."
                )
            if op.tipo in tipos_usados:
                raise ValidationError(
                    "Solo se permite una opcion por tipo."
                )
            tipos_usados.add(op.tipo)
    precio_unitario = producto.precio + sum(
        (op.recargo for op in opciones), Decimal("0")
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


def quitar_item(item):
    if item.pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden quitar items de un carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)


def aplicar_codigo(pedido, texto):
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("Codigo de descuento invalido.")
    if not codigo.activo:
        raise ValidationError("El codigo de descuento no esta activo.")
    hoy = timezone.localdate()
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El codigo de descuento esta vencido.")
    if codigo.solo_primer_pedido:
        tiene_pedidos = Pedido.objects.filter(
            cliente=pedido.cliente
        ).exclude(
            estado__in=[EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO]
        ).exists()
        if tiene_pedidos:
            raise ValidationError(
                "Este codigo es solo para el primer pedido."
            )
    pedido.codigo_descuento = codigo
    pedido.save()
    recalcular_totales(pedido)


def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se puede confirmar un carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito esta vacio.")
    if not direccion or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("Direccion invalida para este cliente.")
    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=EstadoPago.PENDIENTE,
        referencia=str(uuid.uuid4()),
        monto=pedido.total,
    )
    if metodo_pago == MetodoPago.EFECTIVO:
        registrar_estado(pedido, EstadoPedido.RECIBIDO)
    else:
        registrar_estado(pedido, EstadoPedido.PENDIENTE_PAGO)
    return pago


def avanzar_pedido(pedido, nuevo_estado, usuario):
    permitidas = TRANSICIONES.get(pedido.estado, [])
    if nuevo_estado not in permitidas:
        raise ValidationError(
            f"No se puede pasar de {pedido.get_estado_display()} a "
            f"{dict(EstadoPedido.choices)[nuevo_estado]}."
        )

    if nuevo_estado == EstadoPedido.EN_PREPARACION:
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif nuevo_estado == EstadoPedido.LISTO_DESPACHO:
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif nuevo_estado == EstadoPedido.EN_CAMINO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
        with transaction.atomic():
            entrega = Entrega.objects.create(
                pedido=pedido,
                repartidor=usuario,
                inicio=timezone.now(),
            )
            registrar_estado(pedido, nuevo_estado, usuario)
            return entrega
    elif nuevo_estado == EstadoPedido.ENTREGADO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("El pedido no tiene entrega asignada.")
        if entrega.repartidor_id != usuario.id:
            raise ValidationError("Solo el repartidor asignado puede entregar.")
        with transaction.atomic():
            entrega.fin = timezone.now()
            entrega.save()
            registrar_estado(pedido, nuevo_estado, usuario)
            return entrega

    registrar_estado(pedido, nuevo_estado, usuario)


def ventas_periodo(dias):
    desde = timezone.localdate() - timezone.timedelta(days=dias - 1)
    return (
        Pedido.objects.filter(
            estado__gte=EstadoPedido.RECIBIDO,
            creado__date__gte=desde,
        ).aggregate(total=Sum("total"))["total"]
        or Decimal("0")
    )


def productos_mas_pedidos(limite=5):
    return (
        Producto.objects.filter(
            items__pedido__estado__gte=EstadoPedido.RECIBIDO
        )
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades")[:limite]
    )


def ranking_repartidores():
    from collections import defaultdict

    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    datos_por_repartidor = defaultdict(list)
    for e in entregas:
        datos_por_repartidor[e.repartidor_id].append(e)

    resultado = []
    for repartidor_id, lista in datos_por_repartidor.items():
        minutos_list = [e.minutos for e in lista if e.minutos is not None]
        resultado.append(
            {
                "repartidor__id": repartidor_id,
                "repartidor__username": lista[0].repartidor.username,
                "entregas": len(lista),
                "minutos_promedio": (
                    sum(minutos_list) / len(minutos_list) if minutos_list else 0
                ),
            }
        )
    resultado.sort(key=lambda x: x["entregas"], reverse=True)
    return resultado
