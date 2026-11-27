from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido


CENTAVOS = Decimal("0.01")

TRANSICIONES = {
    Pedido.Estado.CARRITO: (Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO),
    Pedido.Estado.PENDIENTE_PAGO: (Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO),
    Pedido.Estado.RECIBIDO: (Pedido.Estado.EN_PREPARACION,),
    Pedido.Estado.EN_PREPARACION: (Pedido.Estado.LISTO_DESPACHO,),
    Pedido.Estado.LISTO_DESPACHO: (Pedido.Estado.EN_CAMINO,),
    Pedido.Estado.EN_CAMINO: (Pedido.Estado.ENTREGADO,),
    Pedido.Estado.ENTREGADO: (),
}

ESTADOS_VENDIDOS = (
    Pedido.Estado.RECIBIDO,
    Pedido.Estado.EN_PREPARACION,
    Pedido.Estado.LISTO_DESPACHO,
    Pedido.Estado.EN_CAMINO,
    Pedido.Estado.ENTREGADO,
)

PERMISOS_TRANSICION = {
    (Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION): "preparar_pedido",
    (Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO): "preparar_pedido",
    (Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO): "despachar_pedido",
    (Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO): "despachar_pedido",
}


@transaction.atomic
def obtener_carrito(usuario):
    """Devuelve o crea el pedido en estado carrito del cliente. (RF-04)"""
    pedido = Pedido.objects.filter(
        cliente=usuario, estado=Pedido.Estado.CARRITO
    ).order_by("pk").first()
    if pedido is None:
        pedido = Pedido.objects.create(cliente=usuario, estado=Pedido.Estado.CARRITO)
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    """Agrega un item al carrito validando producto, cantidad y opciones. (RF-04, RF-05, RF-15)"""
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValidationError("La cantidad debe ser mayor que cero.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    lista_opciones = list(opciones) if opciones is not None else []
    tipos = set()
    recargos = Decimal("0")
    for opcion in lista_opciones:
        if opcion.producto_id != producto.pk:
            raise ValidationError("Las opciones deben pertenecer al producto.")
        if opcion.tipo in tipos:
            raise ValidationError("Solo se permite una opción por tipo.")
        tipos.add(opcion.tipo)
        recargos += Decimal(opcion.recargo)

    precio_unitario = (Decimal(producto.precio) + recargos).quantize(CENTAVOS)
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(lista_opciones)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    """Quita un item del carrito y actualiza los totales. (RF-04)"""
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    item.delete()
    recalcular_totales(pedido)


@transaction.atomic
def recalcular_totales(pedido):
    """Recalcula subtotal, descuento y total con dos decimales. (RF-16)"""
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in pedido.items.all()),
        Decimal("0"),
    ).quantize(CENTAVOS)
    if pedido.codigo_descuento_id:
        porcentaje = Decimal(pedido.codigo_descuento.porcentaje)
        descuento = (subtotal * porcentaje / Decimal("100")).quantize(CENTAVOS)
    else:
        descuento = Decimal("0").quantize(CENTAVOS)
    total = (subtotal - descuento).quantize(CENTAVOS)

    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    """Aplica un código de descuento activo y vigente al pedido. (RF-16)"""
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
        otros_pedidos = Pedido.objects.filter(cliente=pedido.cliente).exclude(
            pk=pedido.pk
        ).exclude(
            estado__in=(Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO)
        )
        if otros_pedidos.exists():
            raise ValidationError("El código solo vale para el primer pedido.")

    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    """Confirma el carrito, crea el Pago y registra el estado inicial. (RF-07)"""
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El pedido no tiene productos.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección no pertenece al cliente.")
    if metodo_pago not in (Pedido.MetodoPago.EFECTIVO, Pedido.MetodoPago.TARJETA):
        raise ValidationError("El método de pago no es válido.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])

    pago = Pago.objects.filter(pedido=pedido).first()
    if pago is None:
        pago = Pago(pedido=pedido)
    pago.metodo = metodo_pago
    pago.estado = Pago.Estado.PENDIENTE
    pago.referencia = str(uuid4())
    pago.monto = pedido.total
    pago.save()
    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO)
    else:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO)
    return pago


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Avanza el estado validando TRANSICIONES y permisos por rol. (RF-12, RF-14)"""
    estado_actual = pedido.estado
    if nuevo_estado not in TRANSICIONES.get(estado_actual, ()):
        raise ValidationError("Transición de estado no permitida.")

    permiso = PERMISOS_TRANSICION.get((estado_actual, nuevo_estado))
    if permiso is None:
        raise ValidationError("Esta transición no se puede realizar desde esta acción.")
    if usuario is None or not usuario.has_perm(f"pedidos.{permiso}"):
        raise ValidationError("No tienes permiso para realizar esta acción.")

    if nuevo_estado == Pedido.Estado.EN_CAMINO:
        Entrega.objects.create(pedido=pedido, repartidor=usuario, inicio=timezone.now())
    elif nuevo_estado == Pedido.Estado.ENTREGADO:
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("El pedido no tiene una entrega asignada.")
        if entrega.repartidor_id != usuario.pk:
            raise ValidationError("Solo el repartidor asignado puede entregar el pedido.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


@transaction.atomic
def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado del pedido y crea su HistorialEstado. (RNF-07)"""
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(
        pedido=pedido, estado=nuevo_estado, usuario=usuario
    )
    return pedido


def ventas_periodo(dias):
    """Suma las ventas de los últimos días, donde 1 significa hoy. (RF-17)"""
    try:
        dias = int(dias)
    except (TypeError, ValueError):
        raise ValidationError("El número de días debe ser mayor que cero.")
    if dias <= 0:
        raise ValidationError("El número de días debe ser mayor que cero.")

    desde = timezone.localdate() - timedelta(days=dias - 1)
    total = Pedido.objects.filter(
        estado__in=ESTADOS_VENDIDOS, creado__date__gte=desde
    ).aggregate(total=Sum("total"))["total"]
    return (total or Decimal("0")).quantize(CENTAVOS)


@transaction.atomic
def productos_mas_pedidos(limite=5):
    """Devuelve los productos con más unidades en pedidos vendidos. (RF-17)"""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        raise ValidationError("El límite debe ser mayor que cero.")
    if limite <= 0:
        raise ValidationError("El límite debe ser mayor que cero.")

    return list(
        ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENDIDOS)
        .values("producto_id", "producto__nombre")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades", "producto__nombre")[:limite]
    )


@transaction.atomic
def ranking_repartidores():
    """Ranking de repartidores por entregas y minutos promedio. (RF-18)"""
    agrupados = {}
    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    for entrega in entregas:
        repartidor = entrega.repartidor
        datos = agrupados.setdefault(
            repartidor.pk,
            {"repartidor": repartidor, "entregas": 0, "minutos_totales": 0},
        )
        datos["entregas"] += 1
        datos["minutos_totales"] += entrega.minutos or 0

    ranking = [
        {
            "repartidor": datos["repartidor"],
            "entregas": datos["entregas"],
            "minutos_promedio": round(
                datos["minutos_totales"] / datos["entregas"], 2
            ),
        }
        for datos in agrupados.values()
    ]
    ranking.sort(key=lambda fila: (-fila["entregas"], fila["repartidor"].username))
    return ranking
