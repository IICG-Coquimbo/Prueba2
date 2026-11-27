from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.pedidos.models import HistorialEstado, ItemPedido, Pedido
from apps.promociones.models import CodigoDescuento

CENTAVOS = Decimal("0.01")
TIPOS_OPCION = ("tamano", "leche", "azucar")
ESTADOS_VENTA = (
    "recibido",
    "en_preparacion",
    "listo_despacho",
    "en_camino",
    "entregado",
)

TRANSICIONES = {
    "carrito": ("recibido", "pendiente_pago"),
    "pendiente_pago": ("recibido", "carrito"),
    "recibido": ("en_preparacion",),
    "en_preparacion": ("listo_despacho",),
    "listo_despacho": ("en_camino",),
    "en_camino": ("entregado",),
    "entregado": (),
}

PERMISOS_TRANSICION = {
    ("recibido", "en_preparacion"): "pedidos.preparar_pedido",
    ("en_preparacion", "listo_despacho"): "pedidos.preparar_pedido",
    ("listo_despacho", "en_camino"): "pedidos.despachar_pedido",
    ("en_camino", "entregado"): "pedidos.despachar_pedido",
}


def _a_decimal(valor):
    return Decimal(str(valor if valor is not None else 0))


def obtener_carrito(usuario):
    """RF-04: devuelve el pedido en carrito del usuario y lo crea si no existe."""
    with transaction.atomic():
        pedido, _creado = Pedido.objects.get_or_create(
            cliente=usuario, estado="carrito"
        )
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: agrega un item al carrito con opciones validadas."""
    if pedido.estado != "carrito":
        raise ValidationError("El pedido no está en carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    seleccionadas = {}
    recargos = Decimal("0")
    for opcion in list(opciones or []):
        if opcion.producto_id != producto.pk:
            raise ValidationError("Las opciones deben pertenecer al producto.")
        if opcion.tipo not in TIPOS_OPCION:
            raise ValidationError("El tipo de opción no es válido.")
        if opcion.tipo in seleccionadas:
            raise ValidationError(
                "Solo se permite una opción por tipo: tamaño, leche o azúcar."
            )
        seleccionadas[opcion.tipo] = opcion
        recargos += _a_decimal(opcion.recargo)

    precio_unitario = (_a_decimal(producto.precio) + recargos).quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )

    with transaction.atomic():
        item = ItemPedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )
        if seleccionadas:
            item.opciones.set(seleccionadas.values())
        recalcular_totales(pedido)
    return item


def quitar_item(item):
    """RF-04, RF-05: quita un item del carrito y recalcula los totales."""
    pedido = item.pedido
    if pedido.estado != "carrito":
        raise ValidationError("Solo se pueden quitar items del carrito.")
    with transaction.atomic():
        item.delete()
        recalcular_totales(pedido)
    return pedido


def recalcular_totales(pedido):
    """RF-05: recalcula subtotal, descuento y total con dos decimales."""
    subtotal = sum(
        (
            _a_decimal(item.precio_unitario) * item.cantidad
            for item in pedido.items.all()
        ),
        Decimal("0"),
    ).quantize(CENTAVOS, rounding=ROUND_HALF_UP)

    descuento = Decimal("0")
    if pedido.codigo_descuento_id is not None:
        porcentaje = _a_decimal(pedido.codigo_descuento.porcentaje)
        descuento = (subtotal * porcentaje / Decimal("100")).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
        )

    total = (subtotal - descuento).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    with transaction.atomic():
        pedido.subtotal = subtotal
        pedido.descuento = descuento
        pedido.total = total
        pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


def aplicar_codigo(pedido, texto):
    """RF-16: valida y aplica un código de descuento al carrito."""
    codigo = CodigoDescuento.objects.filter(codigo=texto).first()
    if codigo is None:
        raise ValidationError("El código de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")

    hoy = timezone.now().date()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código de descuento no está vigente.")

    if codigo.solo_primer_pedido:
        tiene_pedidos = (
            Pedido.objects.filter(cliente=pedido.cliente)
            .exclude(pk=pedido.pk)
            .exclude(estado__in=("carrito", "pendiente_pago"))
            .exists()
        )
        if tiene_pedidos:
            raise ValidationError("El código solo se puede usar en el primer pedido.")

    with transaction.atomic():
        pedido.codigo_descuento = codigo
        pedido.save(update_fields=["codigo_descuento"])
        recalcular_totales(pedido)
    return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: confirma el carrito, crea el pago y registra el cambio de estado."""
    if pedido.estado != "carrito":
        raise ValidationError("El pedido no está en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito está vacío.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección debe pertenecer al cliente.")
    if metodo_pago not in ("efectivo", "tarjeta"):
        raise ValidationError("El método de pago no es válido.")

    with transaction.atomic():
        pago = getattr(pedido, "pago", None)
        if pago is None:
            pago = Pago.objects.create(
                pedido=pedido,
                metodo=metodo_pago,
                estado="pendiente",
                referencia=str(uuid4()),
                monto=pedido.total,
            )
        elif pago.estado == "fallido":
            pago.metodo = metodo_pago
            pago.estado = "pendiente"
            pago.referencia = str(uuid4())
            pago.monto = pedido.total
            pago.save(update_fields=["metodo", "estado", "referencia", "monto"])
        else:
            raise ValidationError("El pedido ya tiene un pago registrado.")

        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago
        pedido.save(update_fields=["direccion", "metodo_pago"])

        if metodo_pago == "efectivo":
            registrar_estado(pedido, "recibido")
        else:
            registrar_estado(pedido, "pendiente_pago")
    return pago


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: valida transición y permiso, y registra el avance del pedido."""
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, ()):
        raise ValidationError("Transición de estado no permitida.")

    permiso = PERMISOS_TRANSICION.get((pedido.estado, nuevo_estado))
    if permiso is None or not usuario.has_perm(permiso):
        raise ValidationError("No tienes permiso para avanzar el pedido.")

    with transaction.atomic():
        if (pedido.estado, nuevo_estado) == ("listo_despacho", "en_camino"):
            Entrega.objects.create(
                pedido=pedido, repartidor=usuario, inicio=timezone.now()
            )
        elif (pedido.estado, nuevo_estado) == ("en_camino", "entregado"):
            entrega = getattr(pedido, "entrega", None)
            if entrega is None or entrega.repartidor_id != usuario.pk:
                raise ValidationError(
                    "Solo el repartidor asignado puede marcar la entrega como entregada."
                )
            entrega.fin = timezone.now()
            entrega.save(update_fields=["fin"])
        registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RNF-07: cambia el estado y crea siempre su registro en el historial."""
    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save(update_fields=["estado"])
        return HistorialEstado.objects.create(
            pedido=pedido, estado=nuevo_estado, usuario=usuario
        )


def ventas_periodo(dias):
    """RF-17: suma de las ventas de los últimos días indicados."""
    if dias < 1:
        raise ValidationError("El número de días debe ser al menos 1.")

    hoy = timezone.now().date()
    desde = hoy - timedelta(days=dias - 1)
    total = Pedido.objects.filter(
        estado__in=ESTADOS_VENTA, creado__date__gte=desde, creado__date__lte=hoy
    ).aggregate(total=Sum("total"))["total"]
    return _a_decimal(total).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def productos_mas_pedidos(limite=5):
    """RF-17: productos con más unidades en pedidos recibidos o posteriores."""
    if limite < 1:
        raise ValidationError("El límite debe ser al menos 1.")
    return (
        Producto.objects.filter(items__pedido__estado__in=ESTADOS_VENTA)
        .annotate(unidades=Sum("items__cantidad"))
        .order_by("-unidades", "nombre")[:limite]
    )


def ranking_repartidores():
    """RF-18: repartidores ordenados por entregas terminadas y minutos promedio."""
    grupos = defaultdict(lambda: {"entregas": 0, "minutos": Decimal("0")})
    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    for entrega in entregas:
        grupo = grupos[entrega.repartidor_id]
        grupo["repartidor"] = entrega.repartidor
        grupo["entregas"] += 1
        if entrega.minutos is not None:
            grupo["minutos"] += _a_decimal(entrega.minutos)

    resultado = []
    for grupo in grupos.values():
        cantidad = grupo["entregas"]
        promedio = (grupo["minutos"] / cantidad).quantize(
            CENTAVOS, rounding=ROUND_HALF_UP
        )
        resultado.append(
            {
                "repartidor": grupo["repartidor"],
                "entregas": cantidad,
                "minutos_promedio": promedio,
            }
        )
    resultado.sort(key=lambda fila: (-fila["entregas"], fila["repartidor"].username))
    return resultado
