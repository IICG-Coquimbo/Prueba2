from decimal import Decimal

import uuid
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado, EstadoPedido
from apps.pagos.models import Pago
from apps.entregas.models import Entrega
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.cuentas.models import Direccion


TRANSICIONES = {
    EstadoPedido.CARRITO: [
        EstadoPedido.RECIBIDO,
        EstadoPedido.PENDIENTE_PAGO,
    ],
    EstadoPedido.PENDIENTE_PAGO: [
        EstadoPedido.CARRITO,
        EstadoPedido.RECIBIDO,
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

ESTADOS_RECIBIDO_O_POSTERIOR = [
    EstadoPedido.RECIBIDO,
    EstadoPedido.EN_PREPARACION,
    EstadoPedido.LISTO_DESPACHO,
    EstadoPedido.EN_CAMINO,
    EstadoPedido.ENTREGADO,
]


def obtener_carrito(usuario):
    """Devuelve el pedido en estado carrito del usuario; si no existe, lo crea. (RF-04)"""
    pedido, _creado = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=EstadoPedido.CARRITO,
    )
    return pedido


def recalcular_totales(pedido):
    """subtotal = suma de cantidad x precio_unitario;
    descuento = subtotal x porcentaje del codigo / 100 (0 si no hay codigo);
    total = subtotal - descuento. Dos decimales."""
    items = pedido.items.all()
    subtotal = sum(
        (item.cantidad * item.precio_unitario for item in items),
        Decimal("0"),
    )
    descuento = Decimal("0")
    if pedido.codigo_descuento_id:
        descuento = subtotal * pedido.codigo_descuento.porcentaje / Decimal(100)
    total = subtotal - descuento
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save()


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado y crea el HistorialEstado. (RNF-07)"""
    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save()
        HistorialEstado.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            usuario=usuario,
        )


def agregar_item(pedido, producto, cantidad, opciones):
    """Exige estado carrito, producto disponible, cantidad mayor que 0,
    opciones que pertenezcan al producto y como maximo una por tipo.
    precio_unitario = precio + recargos de las opciones. Llama a recalcular_totales.
    (RF-04, RF-05, RF-15)"""
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no esta disponible.")
    if cantidad is None or cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor a 0.")

    tipos_vistos = set()
    recargo_total = Decimal("0")
    for opcion in opciones:
        if opcion.producto_id != producto.id:
            raise ValidationError("La opcion no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError("Solo se permite una opcion por tipo.")
        tipos_vistos.add(opcion.tipo)
        recargo_total += opcion.recargo

    precio_unitario = producto.precio + recargo_total

    with transaction.atomic():
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
    """Exige estado carrito. Llama a recalcular_totales."""
    if item.pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("Solo se pueden quitar items de un carrito.")
    pedido = item.pedido
    with transaction.atomic():
        item.delete()
        recalcular_totales(pedido)


def aplicar_codigo(pedido, texto):
    """Busca el CodigoDescuento por codigo. Exige activo, fecha de hoy entre
    vigente_desde y vigente_hasta y, si solo_primer_pedido, que el cliente no
    tenga otros pedidos fuera de carrito y pendiente_pago. Guarda el codigo en
    el pedido y llama a recalcular_totales. (RF-16)"""
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El codigo de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El codigo de descuento no esta activo.")
    hoy = timezone.localdate()
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El codigo de descuento no esta vigente.")
    if codigo.solo_primer_pedido:
        tiene_otros = (
            Pedido.objects.filter(cliente=pedido.cliente)
            .exclude(
                estado__in=[
                    EstadoPedido.CARRITO,
                    EstadoPedido.PENDIENTE_PAGO,
                ]
            )
            .exists()
        )
        if tiene_otros:
            raise ValidationError("Este codigo es solo para el primer pedido.")
    with transaction.atomic():
        pedido.codigo_descuento = codigo
        recalcular_totales(pedido)


def confirmar_pedido(pedido, direccion, metodo_pago):
    """Exige estado carrito, al menos un item y una direccion del mismo cliente.
    Crea el Pago (estado pendiente, referencia uuid4 en texto, monto = total).
    Efectivo: registrar_estado(recibido). Tarjeta:
    registrar_estado(pendiente_pago) y la vista redirige a la pasarela. (RF-07)"""
    if pedido.estado != EstadoPedido.CARRITO:
        raise ValidationError("El pedido debe estar en estado carrito.")
    if pedido.items.count() == 0:
        raise ValidationError("El carrito debe tener al menos un item.")
    if not isinstance(direccion, Direccion) or direccion.usuario != pedido.cliente:
        raise ValidationError("La direccion no pertenece al cliente.")

    with transaction.atomic():
        pago = Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado=Pago.EstadoPago.PENDIENTE,
            referencia=str(uuid.uuid4()),
            monto=pedido.total,
        )
        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago
        if metodo_pago == Pago.MetodoPago.EFECTIVO:
            registrar_estado(pedido, EstadoPedido.RECIBIDO)
        else:
            registrar_estado(pedido, EstadoPedido.PENDIENTE_PAGO)
    return pago


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Valida con TRANSICIONES y por rol: preparar_pedido permite recibido ->
    en_preparacion y en_preparacion -> listo_despacho; despachar_pedido permite
    listo_despacho -> en_camino (crea la Entrega con ese repartidor e inicio =
    ahora) y en_camino -> entregado (solo el repartidor de la Entrega; guarda
    fin = ahora). (RF-12, RF-14)"""
    estado_actual = pedido.estado
    permitidas = TRANSICIONES.get(estado_actual, [])
    if nuevo_estado not in permitidas:
        raise ValidationError("La transicion de estado no esta permitida.")

    if nuevo_estado in (
        EstadoPedido.EN_PREPARACION,
        EstadoPedido.LISTO_DESPACHO,
    ):
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tiene permiso para preparar pedidos.")
    if nuevo_estado in (
        EstadoPedido.EN_CAMINO,
        EstadoPedido.ENTREGADO,
    ):
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar pedidos.")

    with transaction.atomic():
        if nuevo_estado == EstadoPedido.EN_CAMINO:
            Entrega.objects.create(
                pedido=pedido,
                repartidor=usuario,
                inicio=timezone.now(),
            )
        if nuevo_estado == EstadoPedido.ENTREGADO:
            try:
                entrega = pedido.entrega
            except Entrega.DoesNotExist:
                raise ValidationError("No existe entrega para este pedido.")
            if entrega.repartidor_id != usuario.id:
                raise ValidationError(
                    "Solo el repartidor de la entrega puede marcarla como entregada."
                )
            entrega.fin = timezone.now()
            entrega.save()
        registrar_estado(pedido, nuevo_estado, usuario)


def ventas_periodo(dias):
    """Suma del total de los pedidos en estado recibido o posterior creados
    en los ultimos <dias> dias (1 = hoy). (RF-17)"""
    hoy = timezone.localdate()
    desde = hoy - timezone.timedelta(days=dias - 1)
    desde_dt = timezone.make_aware(
        timezone.datetime.combine(desde, timezone.time.min)
    )
    total = (
        Pedido.objects.filter(
            estado__in=ESTADOS_RECIBIDO_O_POSTERIOR,
            creado__gte=desde_dt,
        )
        .aggregate(suma=Sum("total"))["suma"]
        or Decimal("0")
    )
    return total


def productos_mas_pedidos(limite=5):
    """Productos con mas unidades en pedidos recibidos o posteriores. (RF-17)"""
    return (
        Producto.objects.filter(
            items__pedido__estado__in=ESTADOS_RECIBIDO_O_POSTERIOR
        )
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades")[:limite]
    )


def ranking_repartidores():
    """Por repartidor, entregas con fin y minutos promedio, ordenado por
    entregas (mayor primero). (RF-18)"""
    from collections import defaultdict

    datos = defaultdict(
        lambda: {"repartidor": None, "entregas": 0, "minutos": []}
    )
    for entrega in (
        Entrega.objects.filter(fin__isnull=False)
        .select_related("repartidor")
        .order_by("repartidor")
    ):
        r = entrega.repartidor
        datos[r.id]["repartidor"] = r
        datos[r.id]["entregas"] += 1
        if entrega.minutos is not None:
            datos[r.id]["minutos"].append(entrega.minutos)

    resultado = []
    for d in datos.values():
        prom = (
            sum(d["minutos"]) / len(d["minutos"])
            if d["minutos"]
            else 0
        )
        resultado.append(
            {
                "repartidor": d["repartidor"],
                "entregas": d["entregas"],
                "minutos_promedio": round(prom, 2),
            }
        )
    resultado.sort(key=lambda x: x["entregas"], reverse=True)
    return resultado
