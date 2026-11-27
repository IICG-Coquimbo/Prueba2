"""Logica de negocio de pedidos: carrito, estados, pago y reportes."""

import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import OpcionProducto, Producto
from apps.entregas.models import Entrega
from apps.pagos.models import EstadoPago, Pago
from apps.pedidos.models import HistorialEstado, ItemPedido, MetodoPago, Pedido
from apps.promociones.models import CodigoDescuento

CENTAVOS = Decimal("0.01")

TRANSICIONES = {
    "carrito": ["recibido", "pendiente_pago"],
    "pendiente_pago": ["recibido", "carrito"],
    "recibido": ["en_preparacion"],
    "en_preparacion": ["listo_despacho"],
    "listo_despacho": ["en_camino"],
    "en_camino": ["entregado"],
    "entregado": [],
}

ESTADOS_VENDIDOS = [
    "recibido",
    "en_preparacion",
    "listo_despacho",
    "en_camino",
    "entregado",
]

TRANSICIONES_PREPARACION = {
    ("recibido", "en_preparacion"),
    ("en_preparacion", "listo_despacho"),
}

TRANSICIONES_DESPACHO = {
    ("listo_despacho", "en_camino"),
    ("en_camino", "entregado"),
}


def _validar_transicion(pedido, nuevo_estado):
    """RF-09, RNF-07: comprueba que el cambio de estado este en TRANSICIONES."""
    permitidos = TRANSICIONES.get(pedido.estado, [])
    if nuevo_estado not in permitidos:
        raise ValidationError(
            f"Transicion de estado no permitida: de '{pedido.estado}' a '{nuevo_estado}'."
        )


def obtener_carrito(usuario):
    """RF-04: devuelve el pedido en estado carrito del usuario y, si no existe, lo crea."""
    pedido, _creado = Pedido.objects.get_or_create(
        cliente=usuario,
        estado="carrito",
    )
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: agrega un item al carrito con sus opciones y recalcula totales."""
    opciones = list(opciones or [])
    with transaction.atomic():
        if pedido.estado != "carrito":
            raise ValidationError("Solo se pueden agregar productos a un pedido en carrito.")
        if not producto.disponible:
            raise ValidationError("El producto no esta disponible.")
        if cantidad is None or cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")

        recargos = Decimal("0.00")
        tipos_vistos = set()
        for opcion in opciones:
            if not isinstance(opcion, OpcionProducto):
                raise ValidationError("Cada opcion debe ser una opcion del producto.")
            if opcion.producto_id != producto.pk:
                raise ValidationError("Una de las opciones no pertenece al producto.")
            if opcion.tipo in tipos_vistos:
                raise ValidationError(
                    f"Solo se permite una opcion por tipo ('{opcion.tipo}')."
                )
            tipos_vistos.add(opcion.tipo)
            recargos += opcion.recargo

        precio_unitario = (producto.precio + recargos).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
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
    """RF-04: quita un item del carrito y recalcula los totales del pedido."""
    with transaction.atomic():
        pedido = item.pedido
        if pedido.estado != "carrito":
            raise ValidationError("Solo se pueden quitar items de un pedido en carrito.")
        pedido.save()
        item.delete()
        recalcular_totales(pedido)
        return pedido


def recalcular_totales(pedido):
    """RF-04, RF-16: recalcula subtotal, descuento y total del pedido a dos decimales."""
    with transaction.atomic():
        subtotal = sum(
            (item.cantidad * item.precio_unitario for item in pedido.items.all()),
            Decimal("0.00"),
        )
        if pedido.codigo_descuento_id:
            descuento = subtotal * pedido.codigo_descuento.porcentaje / Decimal("100")
        else:
            descuento = Decimal("0.00")
        total = subtotal - descuento

        pedido.subtotal = subtotal.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        pedido.descuento = descuento.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        pedido.total = total.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
        pedido.save()
        return pedido


def aplicar_codigo(pedido, texto):
    """RF-16: valida vigencia y primer pedido del codigo de descuento y recalcula totales."""
    with transaction.atomic():
        codigo = CodigoDescuento.objects.filter(codigo=texto).first()
        if codigo is None:
            raise ValidationError("El codigo de descuento no existe.")
        if not codigo.activo:
            raise ValidationError("El codigo de descuento no esta activo.")

        hoy = timezone.localdate()
        if not codigo.vigente_desde <= hoy <= codigo.vigente_hasta:
            raise ValidationError("El codigo de descuento no esta vigente.")

        if codigo.solo_primer_pedido and Pedido.objects.filter(
            cliente=pedido.cliente,
            estado__in=ESTADOS_VENDIDOS,
        ).exists():
            raise ValidationError(
                "El codigo de descuento solo es valido para el primer pedido."
            )

        pedido.codigo_descuento = codigo
        recalcular_totales(pedido)
        return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: confirma el carrito, crea el Pago pendiente y registra el estado inicial."""
    with transaction.atomic():
        if pedido.estado != "carrito":
            raise ValidationError("El pedido debe estar en carrito para confirmarse.")
        if not pedido.items.exists():
            raise ValidationError("El carrito esta vacio; agregue productos antes de confirmar.")
        if direccion is None or direccion.usuario_id != pedido.cliente_id:
            raise ValidationError("La direccion debe pertenecer al cliente del pedido.")
        if metodo_pago not in MetodoPago.values:
            raise ValidationError("El metodo de pago debe ser efectivo o tarjeta.")

        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago
        pedido.save()

        pago = Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado=EstadoPago.PENDIENTE,
            referencia=str(uuid.uuid4()),
            monto=pedido.total,
        )
        if metodo_pago == "efectivo":
            registrar_estado(pedido, "recibido", None)
        else:
            registrar_estado(pedido, "pendiente_pago", None)
        return pago


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RF-09, RNF-07: cambia el estado del pedido y crea su HistorialEstado."""
    with transaction.atomic():
        _validar_transicion(pedido, nuevo_estado)
        pedido.estado = nuevo_estado
        pedido.save()
        return HistorialEstado.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            usuario=usuario,
        )


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: valida el rol, aplica los efectos de entrega y avanza el estado."""
    with transaction.atomic():
        transicion = (pedido.estado, nuevo_estado)
        _validar_transicion(pedido, nuevo_estado)

        if transicion in TRANSICIONES_PREPARACION:
            if not usuario.has_perm("pedidos.preparar_pedido"):
                raise ValidationError("No tiene permiso para preparar pedidos.")
        elif transicion in TRANSICIONES_DESPACHO:
            if not usuario.has_perm("pedidos.despachar_pedido"):
                raise ValidationError("No tiene permiso para despachar pedidos.")
        else:
            raise ValidationError(
                "Esta transicion de estado no puede ser realizada por el rol del usuario."
            )

        if transicion == ("listo_despacho", "en_camino"):
            Entrega.objects.create(
                pedido=pedido,
                repartidor=usuario,
                inicio=timezone.now(),
            )
        elif transicion == ("en_camino", "entregado"):
            try:
                entrega = pedido.entrega
            except Entrega.DoesNotExist:
                raise ValidationError("El pedido no tiene una entrega registrada.") from None
            if entrega.repartidor_id != usuario.pk:
                raise ValidationError(
                    "Solo el repartidor asignado puede marcar la entrega como entregada."
                )
            entrega.fin = timezone.now()
            entrega.save()

        registrar_estado(pedido, nuevo_estado, usuario)
        return pedido


def ventas_periodo(dias):
    """RF-17: suma las ventas de los ultimos <dias> dias (1 = hoy)."""
    if dias == 1:
        filtro = {"creado__date": timezone.localdate()}
    else:
        filtro = {"creado__gte": timezone.now() - timedelta(days=dias)}

    total = Pedido.objects.filter(
        estado__in=ESTADOS_VENDIDOS,
        **filtro,
    ).aggregate(total=Sum("total"))["total"]
    return (total or Decimal("0.00")).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def productos_mas_pedidos(limite=5):
    """RF-17: devuelve los productos mas pedidos en unidades en pedidos vendidos."""
    return (
        Producto.objects.filter(items__pedido__estado__in=ESTADOS_VENDIDOS)
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades")[:limite]
    )


def ranking_repartidores():
    """RF-18: ranking de repartidores por entregas finalizadas y minutos promedio."""
    por_repartidor = {}
    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    for entrega in entregas:
        datos = por_repartidor.setdefault(
            entrega.repartidor_id,
            {"repartidor": entrega.repartidor, "entregas": 0, "minutos": []},
        )
        datos["entregas"] += 1
        if entrega.minutos is not None:
            datos["minutos"].append(entrega.minutos)

    ranking = []
    for datos in por_repartidor.values():
        minutos = datos["minutos"]
        promedio = float(sum(minutos)) / len(minutos) if minutos else None
        ranking.append(
            {
                "repartidor": datos["repartidor"],
                "entregas": datos["entregas"],
                "minutos_promedio": promedio,
            }
        )
    ranking.sort(key=lambda fila: fila["entregas"], reverse=True)
    return ranking
