"""Lógica de negocio de pedidos (docs/reglas_flujo.md).

Son funciones normales: las vistas las llaman desde form_valid y no
repiten las reglas aquí implementadas.
"""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import OpcionProducto, Producto
from apps.entregas.models import Entrega
from apps.pagos.models import EstadoPago, Pago
from apps.promociones.models import CodigoDescuento

from .models import (
    EstadoPedido,
    HistorialEstado,
    ItemPedido,
    MetodoPago,
    Pedido,
)

CENTAVOS = Decimal("0.01")

# RF-17: una venta es un pedido en estado recibido o posterior.
ESTADOS_VENTA = (
    EstadoPedido.RECIBIDO,
    EstadoPedido.EN_PREPARACION,
    EstadoPedido.LISTO_DESPACHO,
    EstadoPedido.EN_CAMINO,
    EstadoPedido.ENTREGADO,
)

# RF-07, RF-08, RF-12, RF-14: transiciones permitidas. Cualquier otra
# transición es un error.
TRANSICIONES = {
    EstadoPedido.CARRITO.value: [
        EstadoPedido.RECIBIDO.value,
        EstadoPedido.PENDIENTE_PAGO.value,
    ],
    EstadoPedido.PENDIENTE_PAGO.value: [
        EstadoPedido.RECIBIDO.value,
        EstadoPedido.CARRITO.value,
    ],
    EstadoPedido.RECIBIDO.value: [EstadoPedido.EN_PREPARACION.value],
    EstadoPedido.EN_PREPARACION.value: [EstadoPedido.LISTO_DESPACHO.value],
    EstadoPedido.LISTO_DESPACHO.value: [EstadoPedido.EN_CAMINO.value],
    EstadoPedido.EN_CAMINO.value: [EstadoPedido.ENTREGADO.value],
    EstadoPedido.ENTREGADO.value: [],
}


def _valor_estado(estado):
    """Acepta un EstadoPedido, un TextChoices o su valor como texto."""
    return getattr(estado, "value", estado)


def _dos_decimales(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


@transaction.atomic
def obtener_carrito(usuario):
    """Devuelve el pedido en estado carrito del usuario; si no existe, lo crea. (RF-04)"""
    pedido = (
        Pedido.objects.filter(cliente=usuario, estado=EstadoPedido.CARRITO)
        .order_by("pk")
        .first()
    )
    if pedido is None:
        pedido = Pedido.objects.create(cliente=usuario, estado=EstadoPedido.CARRITO)
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    """Agrega un item al carrito con su precio unitario calculado. (RF-04, RF-05, RF-15)"""
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden agregar productos al carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValidationError("La cantidad debe ser un número entero.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    tipos = set()
    recargos = Decimal("0")
    opciones_validas = []
    for opcion in list(opciones or []):
        if isinstance(opcion, (int, str)):
            opcion = OpcionProducto.objects.filter(pk=opcion).first()
            if opcion is None:
                raise ValidationError("Una de las opciones elegidas no existe.")
        if opcion.producto_id != producto.pk:
            raise ValidationError("Cada opción debe pertenecer al producto elegido.")
        if opcion.tipo in tipos:
            raise ValidationError(
                "Solo se permite una opción por tipo (tamaño, leche o azúcar)."
            )
        tipos.add(opcion.tipo)
        recargos += Decimal(opcion.recargo or Decimal("0"))
        opciones_validas.append(opcion)

    precio_unitario = _dos_decimales(Decimal(producto.precio) + recargos)
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(opciones_validas)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    """Quita un item del carrito y recalcula los totales. (RF-04)"""
    pedido = item.pedido
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden quitar items del carrito.")
    item.delete()
    recalcular_totales(pedido)


@transaction.atomic
def recalcular_totales(pedido):
    """Calcula subtotal, descuento y total con dos decimales. (RF-04, RF-16)"""
    subtotal = sum(
        (
            Decimal(item.cantidad) * Decimal(item.precio_unitario)
            for item in pedido.items.all()
        ),
        Decimal("0"),
    )
    subtotal = _dos_decimales(subtotal)

    descuento = Decimal("0")
    if pedido.codigo_descuento is not None:
        descuento = _dos_decimales(
            subtotal * Decimal(pedido.codigo_descuento.porcentaje) / Decimal("100")
        )
    total = _dos_decimales(subtotal - descuento)

    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    """Valida y guarda un código de descuento en el pedido. (RF-16)"""
    codigo = CodigoDescuento.objects.filter(codigo=str(texto).strip()).first()
    if codigo is None:
        raise ValidationError("El código de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")

    hoy = timezone.localdate()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código de descuento no está vigente.")

    if codigo.solo_primer_pedido and pedido.cliente.pedidos.exclude(
        pk=pedido.pk
    ).exclude(
        estado__in=[EstadoPedido.CARRITO, EstadoPedido.PENDIENTE_PAGO]
    ).exists():
        raise ValidationError("Este código solo se puede usar en el primer pedido.")

    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    """Confirma el carrito, crea el Pago y registra el nuevo estado. (RF-07)"""
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido ya no está en el carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito está vacío.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección debe pertenecer al cliente del pedido.")

    metodo = _valor_estado(metodo_pago)
    if metodo not in MetodoPago.values:
        raise ValidationError("El método de pago no es válido.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo
    pedido.save(update_fields=["direccion", "metodo_pago"])

    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo,
        estado=EstadoPago.PENDIENTE,
        referencia=str(uuid4()),
        monto=pedido.total,
    )

    if metodo == MetodoPago.EFECTIVO:
        registrar_estado(pedido, EstadoPedido.RECIBIDO)
    else:
        registrar_estado(pedido, EstadoPedido.PENDIENTE_PAGO)
    return pago


@transaction.atomic
def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado del pedido y crea su HistorialEstado. (RNF-07)"""
    estado = _valor_estado(nuevo_estado)
    if estado not in EstadoPedido.values:
        raise ValidationError("El estado indicado no es válido.")
    pedido.estado = estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=estado, usuario=usuario)
    return pedido


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Avanza el estado validando TRANSICIONES y el permiso por rol. (RF-12, RF-14)"""
    estado = _valor_estado(nuevo_estado)
    if estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError("Este cambio de estado no está permitido.")

    ahora = timezone.now()
    if estado in (EstadoPedido.EN_PREPARACION, EstadoPedido.LISTO_DESPACHO):
        if usuario is None or not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tiene permiso para preparar el pedido.")
    elif estado == EstadoPedido.EN_CAMINO:
        if usuario is None or not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar el pedido.")
        Entrega.objects.create(pedido=pedido, repartidor=usuario, inicio=ahora)
    elif estado == EstadoPedido.ENTREGADO:
        if usuario is None or not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar el pedido.")
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("El pedido no tiene una entrega asignada.")
        if entrega.repartidor_id != usuario.pk:
            raise ValidationError(
                "Solo el repartidor de la entrega puede marcar el pedido como entregado."
            )
        entrega.fin = ahora
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, estado, usuario)
    return pedido


def ventas_periodo(dias):
    """Suma de ventas de los últimos <dias> días (1 = hoy). (RF-17)"""
    try:
        dias = int(dias)
    except (TypeError, ValueError):
        raise ValidationError("El número de días debe ser un entero.")
    if dias < 1:
        raise ValidationError("El número de días debe ser mayor que cero.")

    desde = timezone.localdate() - timedelta(days=dias - 1)
    total = Pedido.objects.filter(
        estado__in=ESTADOS_VENTA,
        creado__date__gte=desde,
    ).aggregate(total=Sum("total"))["total"]
    return _dos_decimales(total or Decimal("0"))


def productos_mas_pedidos(limite=5):
    """Productos con más unidades en pedidos recibidos o posteriores. (RF-17)"""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        raise ValidationError("El límite debe ser un entero.")
    if limite < 1:
        raise ValidationError("El límite debe ser mayor que cero.")

    return (
        Producto.objects.filter(items__pedido__estado__in=ESTADOS_VENTA)
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades", "pk")[:limite]
    )


def ranking_repartidores():
    """Ranking por repartidor: entregas con fin y minutos promedio. (RF-18)

    Devuelve una lista de diccionarios con las claves ``repartidor``
    (User), ``entregas`` (cantidad) y ``minutos_promedio``, ordenada
    de mayor a menor cantidad de entregas.
    """
    ranking = []
    repartidores = User.objects.filter(entregas__fin__isnull=False).distinct()
    for repartidor in repartidores:
        entregas = list(repartidor.entregas.filter(fin__isnull=False))
        cantidad = len(entregas)
        promedio = sum(entrega.minutos for entrega in entregas) / cantidad
        ranking.append(
            {
                "repartidor": repartidor,
                "entregas": cantidad,
                "minutos_promedio": round(promedio, 2),
            }
        )
    ranking.sort(key=lambda fila: (-fila["entregas"], fila["repartidor"].pk))
    return ranking
