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
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido

TRANSICIONES = {
    "carrito": ["recibido", "pendiente_pago"],
    "pendiente_pago": ["recibido", "carrito"],
    "recibido": ["en_preparacion"],
    "en_preparacion": ["listo_despacho"],
    "listo_despacho": ["en_camino"],
    "en_camino": ["entregado"],
    "entregado": [],
}

_ESTADOS_CONFIRMADOS = (
    "recibido",
    "en_preparacion",
    "listo_despacho",
    "en_camino",
    "entregado",
)

_CENTAVOS = Decimal("0.01")


def obtener_carrito(usuario):
    """Devuelve el pedido en carrito del usuario y lo crea si no existe (RF-04)."""
    pedido, _ = Pedido.objects.get_or_create(cliente=usuario, estado="carrito")
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """Agrega un producto con sus opciones al carrito y recalcula totales (RF-04, RF-05, RF-15)."""
    with transaction.atomic():
        if pedido.estado != "carrito":
            raise ValidationError("Solo se pueden agregar productos al carrito.")
        if not producto.disponible:
            raise ValidationError("El producto no está disponible.")
        if cantidad is None or cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")

        opciones = list(opciones or [])
        tipos = set()
        recargos = Decimal("0.00")
        for opcion in opciones:
            if opcion.producto_id != producto.pk:
                raise ValidationError("Las opciones deben pertenecer al producto.")
            if opcion.tipo in tipos:
                raise ValidationError(
                    f"Solo se permite una opción de tipo {opcion.tipo}."
                )
            tipos.add(opcion.tipo)
            recargos += Decimal(str(opcion.recargo or 0))

        precio_unitario = (Decimal(str(producto.precio)) + recargos).quantize(
            _CENTAVOS, rounding=ROUND_HALF_UP
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
    """Quita un item del carrito y recalcula totales (RF-04)."""
    with transaction.atomic():
        pedido = item.pedido
        if pedido.estado != "carrito":
            raise ValidationError("Solo se pueden quitar productos del carrito.")
        item.delete()
        recalcular_totales(pedido)
        return pedido


def recalcular_totales(pedido):
    """Recalcula subtotal, descuento y total del pedido (RF-05)."""
    subtotal = sum(
        (
            Decimal(item.cantidad) * Decimal(str(item.precio_unitario))
            for item in pedido.items.all()
        ),
        Decimal("0.00"),
    ).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)

    descuento = Decimal("0.00")
    if pedido.codigo_descuento_id:
        porcentaje = Decimal(str(pedido.codigo_descuento.porcentaje))
        descuento = (subtotal * porcentaje / Decimal("100")).quantize(
            _CENTAVOS, rounding=ROUND_HALF_UP
        )

    total = (subtotal - descuento).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


def aplicar_codigo(pedido, texto):
    """Aplica un código de descuento activo y vigente al pedido (RF-16)."""
    with transaction.atomic():
        try:
            codigo = CodigoDescuento.objects.get(codigo=texto)
        except CodigoDescuento.DoesNotExist:
            raise ValidationError("El código de descuento no existe.") from None

        if not codigo.activo:
            raise ValidationError("El código de descuento no está activo.")

        hoy = timezone.now().date()
        if not codigo.vigente_desde <= hoy <= codigo.vigente_hasta:
            raise ValidationError("El código de descuento no está vigente.")

        if codigo.solo_primer_pedido:
            tiene_pedidos = (
                pedido.cliente.pedidos.exclude(pk=pedido.pk)
                .exclude(estado__in=("carrito", "pendiente_pago"))
                .exists()
            )
            if tiene_pedidos:
                raise ValidationError(
                    "El código solo se puede usar en el primer pedido."
                )

        pedido.codigo_descuento = codigo
        pedido.save(update_fields=["codigo_descuento"])
        recalcular_totales(pedido)
        return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    """Confirma el carrito, crea el pago y registra el estado inicial (RF-07)."""
    with transaction.atomic():
        if pedido.estado != "carrito":
            raise ValidationError("El pedido no está en el carrito.")
        if not pedido.items.exists():
            raise ValidationError("El carrito está vacío.")
        if direccion is None or direccion.usuario_id != pedido.cliente_id:
            raise ValidationError("La dirección no pertenece al cliente.")
        if metodo_pago not in ("efectivo", "tarjeta"):
            raise ValidationError("El método de pago no es válido.")

        pago = Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado="pendiente",
            referencia=str(uuid4()),
            monto=pedido.total,
        )
        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago
        pedido.save(update_fields=["direccion", "metodo_pago"])

        estado = "recibido" if metodo_pago == "efectivo" else "pendiente_pago"
        registrar_estado(pedido, estado)
        return pago


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado del pedido y registra el historial (RNF-07)."""
    with transaction.atomic():
        estado_actual = pedido.estado
        if nuevo_estado not in TRANSICIONES.get(estado_actual, []):
            raise ValidationError(
                f"No se puede cambiar de {estado_actual} a {nuevo_estado}."
            )

        pedido.estado = nuevo_estado
        pedido.save(update_fields=["estado"])
        HistorialEstado.objects.create(
            pedido=pedido, estado=nuevo_estado, usuario=usuario
        )
        return pedido


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Avanza el pedido validando transición, permisos y entrega (RF-12, RF-14)."""
    with transaction.atomic():
        estado_actual = pedido.estado
        if nuevo_estado not in TRANSICIONES.get(estado_actual, []):
            raise ValidationError(
                f"No se puede cambiar de {estado_actual} a {nuevo_estado}."
            )

        transicion = (estado_actual, nuevo_estado)
        permisos = {
            ("recibido", "en_preparacion"): "preparar_pedido",
            ("en_preparacion", "listo_despacho"): "preparar_pedido",
            ("listo_despacho", "en_camino"): "despachar_pedido",
            ("en_camino", "entregado"): "despachar_pedido",
        }
        permiso = permisos.get(transicion)
        if permiso is None:
            raise ValidationError("Ese cambio de estado no se puede avanzar.")
        if usuario is None or not usuario.has_perm(f"pedidos.{permiso}"):
            if permiso == "preparar_pedido":
                raise ValidationError("No tienes permiso para preparar pedidos.")
            raise ValidationError("No tienes permiso para despachar pedidos.")

        if transicion == ("listo_despacho", "en_camino"):
            Entrega.objects.create(
                pedido=pedido, repartidor=usuario, inicio=timezone.now()
            )
        elif transicion == ("en_camino", "entregado"):
            try:
                entrega = Entrega.objects.get(pedido=pedido)
            except Entrega.DoesNotExist:
                raise ValidationError(
                    "El pedido no tiene una entrega asignada."
                ) from None
            if entrega.repartidor_id != usuario.pk:
                raise ValidationError(
                    "Solo el repartidor asignado puede entregar el pedido."
                )
            entrega.fin = timezone.now()
            entrega.save(update_fields=["fin"])

        return registrar_estado(pedido, nuevo_estado, usuario)


def ventas_periodo(dias):
    """Suma las ventas confirmadas desde el inicio del periodo (RF-17)."""
    if dias < 1:
        raise ValidationError("El número de días debe ser al menos 1.")

    ahora = timezone.now()
    inicio = (ahora - timedelta(days=dias - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    total = (
        Pedido.objects.filter(
            estado__in=_ESTADOS_CONFIRMADOS, creado__gte=inicio
        ).aggregate(total=Sum("total"))["total"]
        or Decimal("0.00")
    )
    return total.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def productos_mas_pedidos(limite=5):
    """Devuelve los productos más pedidos por unidades confirmadas (RF-17)."""
    if limite < 1:
        raise ValidationError("El límite debe ser al menos 1.")

    return (
        Producto.objects.filter(items__pedido__estado__in=_ESTADOS_CONFIRMADOS)
        .annotate(total_unidades=Sum("items__cantidad"))
        .order_by("-total_unidades")[:limite]
    )


def ranking_repartidores():
    """Calcula entregas y minutos promedio por repartidor (RF-18)."""
    agrupados = {}
    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")
    for entrega in entregas:
        repartidor = entrega.repartidor
        datos = agrupados.setdefault(
            repartidor.pk,
            {"repartidor": repartidor, "entregas": 0, "minutos": []},
        )
        datos["entregas"] += 1
        if entrega.minutos is not None:
            datos["minutos"].append(Decimal(str(entrega.minutos)))

    resultados = []
    for datos in agrupados.values():
        minutos = datos["minutos"]
        promedio = (
            (sum(minutos) / Decimal(len(minutos))).quantize(
                _CENTAVOS, rounding=ROUND_HALF_UP
            )
            if minutos
            else Decimal("0.00")
        )
        resultados.append(
            {
                "repartidor": datos["repartidor"],
                "entregas": datos["entregas"],
                "minutos_promedio": promedio,
            }
        )
    return sorted(resultados, key=lambda fila: fila["entregas"], reverse=True)
