from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido

TRANSICIONES = {
    Pedido.Estado.CARRITO: [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO],
    Pedido.Estado.PENDIENTE_PAGO: [Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO],
    Pedido.Estado.RECIBIDO: [Pedido.Estado.EN_PREPARACION],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.LISTO_DESPACHO],
    Pedido.Estado.LISTO_DESPACHO: [Pedido.Estado.EN_CAMINO],
    Pedido.Estado.EN_CAMINO: [Pedido.Estado.ENTREGADO],
    Pedido.Estado.ENTREGADO: [],
}

ESTADOS_VENDIDOS = [
    Pedido.Estado.RECIBIDO,
    Pedido.Estado.EN_PREPARACION,
    Pedido.Estado.LISTO_DESPACHO,
    Pedido.Estado.EN_CAMINO,
    Pedido.Estado.ENTREGADO,
]


def obtener_carrito(usuario):
    """RF-04: devuelve el carrito del cliente y lo crea si no existe."""
    pedido = Pedido.objects.filter(cliente=usuario, estado=Pedido.Estado.CARRITO).order_by("-creado").first()
    if pedido is None:
        pedido = Pedido.objects.create(cliente=usuario, estado=Pedido.Estado.CARRITO)
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: agrega un item al carrito con sus opciones."""
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido ya no es un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no esta disponible.")
    if not cantidad or cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    opciones = list(opciones)
    tipos = set()
    recargo = Decimal("0")
    for opcion in opciones:
        if opcion.producto_id != producto.pk:
            raise ValidationError("Las opciones no pertenecen al producto.")
        if opcion.tipo in tipos:
            raise ValidationError("Solo se permite una opcion por tipo.")
        tipos.add(opcion.tipo)
        recargo += opcion.recargo

    with transaction.atomic():
        item = ItemPedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio + recargo,
        )
        if opciones:
            item.opciones.set(opciones)
        recalcular_totales(pedido)
    return item


def quitar_item(item):
    """RF-04: quita un item del carrito y recalcula los totales."""
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido ya no es un carrito.")
    with transaction.atomic():
        item.delete()
        recalcular_totales(pedido)


def recalcular_totales(pedido):
    """RF-04, RF-16: calcula subtotal, descuento y total con dos decimales."""
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in pedido.items.all()),
        Decimal("0"),
    )
    descuento = Decimal("0")
    if pedido.codigo_descuento_id:
        descuento = subtotal * Decimal(pedido.codigo_descuento.porcentaje) / Decimal("100")
    total = subtotal - descuento
    moneda = Decimal("0.01")
    pedido.subtotal = subtotal.quantize(moneda, rounding=ROUND_HALF_UP)
    pedido.descuento = descuento.quantize(moneda, rounding=ROUND_HALF_UP)
    pedido.total = total.quantize(moneda, rounding=ROUND_HALF_UP)
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


def aplicar_codigo(pedido, texto):
    """RF-16: valida y aplica un codigo de descuento vigente al carrito."""
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido ya no es un carrito.")
    codigo = CodigoDescuento.objects.filter(codigo__iexact=texto.strip()).first()
    if codigo is None:
        raise ValidationError("El codigo de descuento no existe.")
    hoy = timezone.localdate()
    if not codigo.activo:
        raise ValidationError("El codigo de descuento no esta activo.")
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El codigo de descuento no esta vigente.")
    if codigo.solo_primer_pedido and Pedido.objects.filter(cliente=pedido.cliente).exclude(
        estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]
    ).exists():
        raise ValidationError("Este codigo solo es valido en el primer pedido.")
    with transaction.atomic():
        pedido.codigo_descuento = codigo
        pedido.save(update_fields=["codigo_descuento"])
        recalcular_totales(pedido)
    return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: confirma el carrito y crea el pago segun el metodo elegido."""
    from apps.pagos.models import Pago

    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido ya no es un carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito esta vacio.")
    if direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La direccion no pertenece al cliente.")
    if metodo_pago not in Pedido.MetodoPago.values:
        raise ValidationError("El metodo de pago no es valido.")

    with transaction.atomic():
        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago
        pedido.save(update_fields=["direccion", "metodo_pago"])
        Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado=Pago.Estado.PENDIENTE,
            referencia=str(uuid4()),
            monto=pedido.total,
        )
        if metodo_pago == Pedido.MetodoPago.EFECTIVO:
            registrar_estado(pedido, Pedido.Estado.RECIBIDO, pedido.cliente)
        else:
            registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO, pedido.cliente)
    return pedido


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: valida la transicion por rol y crea la entrega cuando corresponde."""
    actual = pedido.estado
    if nuevo_estado not in TRANSICIONES.get(actual, []):
        raise ValidationError("Transicion de estado no permitida.")

    if actual in (Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION):
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif actual in (Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO):
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
        if actual == Pedido.Estado.EN_CAMINO:
            entrega = getattr(pedido, "entrega", None)
            if entrega is None or entrega.repartidor_id != usuario.pk:
                raise ValidationError("Este pedido no esta a cargo de este repartidor.")
    else:
        raise ValidationError("No puedes avanzar este pedido.")

    with transaction.atomic():
        registrar_estado(pedido, nuevo_estado, usuario)
        if actual == Pedido.Estado.LISTO_DESPACHO and nuevo_estado == Pedido.Estado.EN_CAMINO:
            from apps.entregas.models import Entrega

            Entrega.objects.get_or_create(
                pedido=pedido,
                defaults={"repartidor": usuario, "inicio": timezone.now()},
            )
        elif actual == Pedido.Estado.EN_CAMINO and nuevo_estado == Pedido.Estado.ENTREGADO:
            entrega = getattr(pedido, "entrega", None)
            if entrega is not None:
                entrega.fin = timezone.now()
                entrega.save(update_fields=["fin"])
    return pedido


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RNF-07: cambia el estado y deja constancia en el historial."""
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)


def ventas_periodo(dias):
    """RF-17: suma las ventas de los ultimos dias (1 = hoy)."""
    desde = timezone.localtime() - timedelta(days=max(int(dias), 1) - 1)
    desde = desde.replace(hour=0, minute=0, second=0, microsecond=0)
    total = Pedido.objects.filter(estado__in=ESTADOS_VENDIDOS, creado__gte=desde).aggregate(
        total=Sum("total")
    )["total"]
    return total or Decimal("0")


def productos_mas_pedidos(limite=5):
    """RF-17: productos con mas unidades vendidas."""
    return (
        ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENDIDOS)
        .values("producto__nombre")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades")[:limite]
    )


def ranking_repartidores():
    """RF-18: ranking por entregas y minutos promedio."""
    from apps.entregas.models import Entrega

    datos = {}
    for entrega in Entrega.objects.filter(fin__isnull=False).select_related("repartidor"):
        fila = datos.setdefault(
            entrega.repartidor,
            {"repartidor": entrega.repartidor, "entregas": 0, "minutos": 0},
        )
        fila["entregas"] += 1
        fila["minutos"] += entrega.minutos or 0
    ranking = []
    for fila in datos.values():
        fila["promedio"] = round(fila["minutos"] / fila["entregas"], 2) if fila["entregas"] else 0
        ranking.append(fila)
    return sorted(ranking, key=lambda fila: fila["entregas"], reverse=True)
