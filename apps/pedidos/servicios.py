import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta

from .models import Pedido, ItemPedido, HistorialEstado, EstadoPedido
from apps.cuentas.models import Direccion
from apps.catalogo.models import Producto, OpcionProducto
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento
from apps.entregas.models import Entrega


TRANSICIONES = {
    EstadoPedido.CARRITO: [EstadoPedido.RECIBIDO, EstadoPedido.PENDIENTE_PAGO],
    EstadoPedido.PENDIENTE_PAGO: [EstadoPedido.RECIBIDO, EstadoPedido.CARRITO],
    EstadoPedido.RECIBIDO: [EstadoPedido.EN_PREPARACION],
    EstadoPedido.EN_PREPARACION: [EstadoPedido.LISTO_DESPACHO],
    EstadoPedido.LISTO_DESPACHO: [EstadoPedido.EN_CAMINO],
    EstadoPedido.EN_CAMINO: [EstadoPedido.ENTREGADO],
    EstadoPedido.ENTREGADO: [],
}


def registrar_estado(pedido, nuevo_estado, usuario=None):
    pedido.estado = nuevo_estado
    pedido.save()
    HistorialEstado.objects.create(
        pedido=pedido, estado=nuevo_estado, usuario=usuario
    )
    return pedido


def obtener_carrito(usuario):
    carrito = Pedido.objects.filter(
        cliente=usuario, estado=EstadoPedido.CARRITO
    ).first()
    if not carrito:
        carrito = Pedido.objects.create(
            cliente=usuario, estado=EstadoPedido.CARRITO
        )
    return carrito


def recalcular_totales(pedido):
    items = pedido.items.all()
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in items), Decimal("0")
    )
    descuento = Decimal("0")
    if pedido.codigo_descuento_id:
        descuento = (subtotal * pedido.codigo_descuento.porcentaje) / Decimal("100")
    total = subtotal - descuento
    pedido.subtotal = subtotal.quantize(Decimal("0.01"))
    pedido.descuento = descuento.quantize(Decimal("0.01"))
    pedido.total = total.quantize(Decimal("0.01"))
    pedido.save()
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no est\u00e1 disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")
    tipos_vistos = set()
    for opcion in opciones:
        if opcion.producto_id != producto.id:
            raise ValidationError("La opci\u00f3n no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError("Solo se permite una opci\u00f3n por tipo.")
        tipos_vistos.add(opcion.tipo)
    precio_unitario = producto.precio + sum(
        (o.recargo for o in opciones), Decimal("0")
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
        raise ValidationError("El c\u00f3digo de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El c\u00f3digo de descuento no est\u00e1 activo.")
    hoy = timezone.now().date()
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El c\u00f3digo de descuento no est\u00e1 vigente.")
    if codigo.solo_primer_pedido:
        tiene_otros = Pedido.objects.filter(cliente=pedido.cliente).exclude(
            estado__in=[EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO]
        ).exists()
        if tiene_otros:
            raise ValidationError(
                "Este c\u00f3digo es solo para el primer pedido."
            )
    pedido.codigo_descuento = codigo
    recalcular_totales(pedido)
    return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido debe estar en estado carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito debe tener al menos un item.")
    if direccion.usuario_id != pedido.cliente_id:
        raise ValidationError(
            "La direcci\u00f3n no pertenece al cliente del pedido."
        )
    with transaction.atomic():
        pago = Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado="pendiente",
            referencia=str(uuid.uuid4()),
            monto=pedido.total,
        )
        if metodo_pago == "efectivo":
            registrar_estado(pedido, EstadoPedido.RECIBIDO)
        else:
            registrar_estado(pedido, EstadoPedido.PENDIENTE_PAGO)
    return pago


def avanzar_pedido(pedido, nuevo_estado, usuario):
    estado_actual = pedido.estado
    destinos = TRANSICIONES.get(estado_actual, [])
    if nuevo_estado not in destinos:
        raise ValidationError(
            f"No se puede pasar de {estado_actual} a {nuevo_estado}."
        )
    if nuevo_estado in (
        EstadoPedido.EN_PREPARACION,
        EstadoPedido.LISTO_DESPACHO,
    ):
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError(
                "No tiene permiso para preparar pedidos."
            )
    elif nuevo_estado in (
        EstadoPedido.EN_CAMINO,
        EstadoPedido.ENTREGADO,
    ):
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError(
                "No tiene permiso para despachar pedidos."
            )
    if nuevo_estado == EstadoPedido.EN_CAMINO:
        Entrega.objects.create(
            pedido=pedido, repartidor=usuario, inicio=timezone.now()
        )
    elif nuevo_estado == EstadoPedido.ENTREGADO:
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError(
                "No hay entrega registrada para este pedido."
            )
        if entrega.repartidor_id != usuario.id:
            raise ValidationError(
                "Solo el repartidor asignado puede marcar como entregado."
            )
        entrega.fin = timezone.now()
        entrega.save()
    registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


def ventas_periodo(dias):
    fecha_limite = timezone.now() - timedelta(days=dias - 1)
    fecha_limite = fecha_limite.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    estados_posteriores = [
        EstadoPedido.RECIBIDO,
        EstadoPedido.EN_PREPARACION,
        EstadoPedido.LISTO_DESPACHO,
        EstadoPedido.EN_CAMINO,
        EstadoPedido.ENTREGADO,
    ]
    resultado = Pedido.objects.filter(
        estado__in=estados_posteriores, creado__gte=fecha_limite
    ).aggregate(total=Sum("total"))["total"]
    return resultado or Decimal("0")


def productos_mas_pedidos(limite=5):
    estados_posteriores = [
        EstadoPedido.RECIBIDO,
        EstadoPedido.EN_PREPARACION,
        EstadoPedido.LISTO_DESPACHO,
        EstadoPedido.EN_CAMINO,
        EstadoPedido.ENTREGADO,
    ]
    return Producto.objects.filter(
        items__pedido__estado__in=estados_posteriores
    ).annotate(
        total_unidades=Sum("items__cantidad")
    ).order_by("-total_unidades")[:limite]


def ranking_repartidores():
    from django.contrib.auth.models import User

    repartidores = {}
    for entrega in Entrega.objects.filter(
        fin__isnull=False
    ).select_related("repartidor"):
        rid = entrega.repartidor_id
        if rid not in repartidores:
            repartidores[rid] = {"entregas": 0, "minutos": []}
        repartidores[rid]["entregas"] += 1
        if entrega.minutos is not None:
            repartidores[rid]["minutos"].append(entrega.minutos)
    resultado = []
    for rid, datos in repartidores.items():
        usuario = User.objects.get(pk=rid)
        promedio = (
            sum(datos["minutos"]) / len(datos["minutos"])
            if datos["minutos"]
            else 0
        )
        resultado.append(
            {
                "repartidor": usuario,
                "entregas": datos["entregas"],
                "minutos_promedio": round(promedio, 2),
            }
        )
    resultado.sort(key=lambda x: x["entregas"], reverse=True)
    return resultado
