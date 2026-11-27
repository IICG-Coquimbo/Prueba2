"""Servicios de la app pedidos segun docs/reglas_flujo.md.

Toda la logica de negocio vive aqui. Las vistas las llaman desde form_valid
y no repiten la logica.
"""

import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import HistorialEstado, ItemPedido, Pedido


TRANSICIONES = {
    Pedido.Estado.CARRITO: [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.PENDIENTE_PAGO,
    ],
    Pedido.Estado.PENDIENTE_PAGO: [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.CARRITO,
    ],
    Pedido.Estado.RECIBIDO: [
        Pedido.Estado.EN_PREPARACION,
    ],
    Pedido.Estado.EN_PREPARACION: [
        Pedido.Estado.LISTO_DESPACHO,
    ],
    Pedido.Estado.LISTO_DESPACHO: [
        Pedido.Estado.EN_CAMINO,
    ],
    Pedido.Estado.EN_CAMINO: [
        Pedido.Estado.ENTREGADO,
    ],
    Pedido.Estado.ENTREGADO: [],
}


def obtener_carrito(usuario):
    """Devuelve el pedido en estado carrito del usuario; si no existe, lo crea."""
    carrito = Pedido.objects.filter(
        cliente=usuario, estado=Pedido.Estado.CARRITO
    ).first()
    if carrito is None:
        carrito = Pedido.objects.create(
            cliente=usuario, estado=Pedido.Estado.CARRITO
        )
    return carrito


def _precio_unitario_con_opciones(producto, opciones):
    """Calcula precio del producto mas los recargos de las opciones."""
    precio = producto.precio
    for opcion in opciones:
        precio += opcion.recargo
    return precio


def _validar_opciones(producto, opciones):
    """Valida que las opciones pertenezcan al producto y como maximo una por tipo."""
    tipos_vistos = set()
    for opcion in opciones:
        if opcion.producto_id != producto.pk:
            raise ValidationError(
                f"La opcion '{opcion.nombre}' no pertenece al producto '{producto.nombre}'."
            )
        if opcion.tipo in tipos_vistos:
            raise ValidationError(
                f"Solo se permite una opcion de tipo '{opcion.get_tipo_display()}' por producto."
            )
        tipos_vistos.add(opcion.tipo)


def agregar_item(pedido, producto, cantidad, opciones):
    """Agrega un item al carrito.

    Exige estado carrito, producto disponible, cantidad mayor que 0,
    opciones que pertenezcan al producto y como maximo una por tipo.
    precio_unitario = precio + recargos de las opciones.
    """
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError(f"El producto '{producto.nombre}' no esta disponible.")
    if cantidad is None or cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    opciones = list(opciones)
    _validar_opciones(producto, opciones)

    precio_unitario = _precio_unitario_con_opciones(producto, opciones)

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
    """Quita un item del carrito. Exige estado carrito."""
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden quitar items de un carrito.")
    with transaction.atomic():
        item.delete()
    recalcular_totales(pedido)


def recalcular_totales(pedido):
    """Recalcula subtotal, descuento y total del pedido."""
    subtotal = sum(
        item.cantidad * item.precio_unitario for item in pedido.items.all()
    )
    descuento = 0
    if pedido.codigo_descuento is not None:
        descuento = subtotal * pedido.codigo_descuento.porcentaje / 100
    total = subtotal - descuento
    pedido.subtotal = round(subtotal, 2)
    pedido.descuento = round(descuento, 2)
    pedido.total = round(total, 2)
    pedido.save()


def aplicar_codigo(pedido, texto):
    """Aplica un CodigoDescuento al pedido.

    Exige activo, fecha de hoy entre vigente_desde y vigente_hasta y,
    si solo_primer_pedido, que el cliente no tenga otros pedidos fuera
    de carrito y pendiente_pago.
    """
    from apps.promociones.models import CodigoDescuento

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
        tiene_otros = Pedido.objects.filter(
            cliente=pedido.cliente,
        ).exclude(
            estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO],
        ).exists()
        if tiene_otros:
            raise ValidationError(
                "Este codigo solo puede usarse en el primer pedido del cliente."
            )

    with transaction.atomic():
        pedido.codigo_descuento = codigo
        pedido.save()
    recalcular_totales(pedido)


def confirmar_pedido(pedido, direccion, metodo_pago):
    """Confirma el carrito y crea el Pago.

    Exige estado carrito, al menos un item y una direccion del mismo cliente.
    Crea el Pago (estado pendiente, referencia uuid4 en texto, monto = total).
    Efectivo: registrar_estado(recibido).
    Tarjeta: registrar_estado(pendiente_pago) y la vista redirige a la pasarela.
    """
    from apps.pagos.models import Pago

    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede confirmar un carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito no tiene items.")
    if direccion is None or direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La direccion no pertenece al cliente.")

    with transaction.atomic():
        pago, creado = Pago.objects.get_or_create(
            pedido=pedido,
            defaults={
                "metodo": metodo_pago,
                "estado": Pago.Estado.PENDIENTE,
                "referencia": str(uuid.uuid4()),
                "monto": pedido.total,
            },
        )
        if not creado:
            pago.metodo = metodo_pago
            pago.estado = Pago.Estado.PENDIENTE
            pago.referencia = str(uuid.uuid4())
            pago.monto = pedido.total
            pago.save()
        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago

        if metodo_pago == Pedido.MetodoPago.EFECTIVO:
            registrar_estado(pedido, Pedido.Estado.RECIBIDO)
        else:
            registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO)
        pedido.save()

    return pago


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado del pedido y crea una fila de HistorialEstado."""
    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save()
        HistorialEstado.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            usuario=usuario,
        )


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Valida con TRANSICIONES y por rol, y avanza el estado del pedido."""
    estado_actual = pedido.estado
    permitidas = TRANSICIONES.get(estado_actual, [])
    if nuevo_estado not in permitidas:
        raise ValidationError(
            f"No se puede pasar de '{estado_actual}' a '{nuevo_estado}'."
        )

    from apps.entregas.models import Entrega

    if nuevo_estado in (
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
    ):
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tienes permiso para preparar pedidos.")
        registrar_estado(pedido, nuevo_estado, usuario=usuario)

    elif nuevo_estado == Pedido.Estado.EN_CAMINO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
        with transaction.atomic():
            registro_existente = Entrega.objects.filter(pedido=pedido).first()
            if registro_existente is None:
                Entrega.objects.create(
                    pedido=pedido,
                    repartidor=usuario,
                    inicio=timezone.now(),
                )
            registrar_estado(pedido, nuevo_estado, usuario=usuario)

    elif nuevo_estado == Pedido.Estado.ENTREGADO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tienes permiso para despachar pedidos.")
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("El pedido no tiene una entrega asociada.")
        if entrega.repartidor_id != usuario.pk:
            raise ValidationError(
                "Solo el repartidor asignado puede entregar este pedido."
            )
        with transaction.atomic():
            registrar_estado(pedido, nuevo_estado, usuario=usuario)
            entrega.fin = timezone.now()
            entrega.save()

    else:
        registrar_estado(pedido, nuevo_estado, usuario=usuario)


def ventas_periodo(dias):
    """Suma del total de los pedidos en estado recibido o posterior creados
    en los ultimos <dias> dias (1 = hoy)."""
    fecha_limite = timezone.now() - timedelta(days=dias)
    estados_validos = [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
        Pedido.Estado.EN_CAMINO,
        Pedido.Estado.ENTREGADO,
    ]
    pedidos = Pedido.objects.filter(
        estado__in=estados_validos,
        creado__gte=fecha_limite,
    )
    return sum(p.total for p in pedidos)


def productos_mas_pedidos(limite=5):
    """Productos con mas unidades en pedidos recibidos o posteriores."""
    from apps.catalogo.models import Producto

    estados_validos = [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
        Pedido.Estado.EN_CAMINO,
        Pedido.Estado.ENTREGADO,
    ]
    productos = (
        Producto.objects.filter(
            items__pedido__estado__in=estados_validos,
        )
        .annotate(total_unidades=Sum("items__cantidad"))
        .order_by("-total_unidades")[:limite]
    )
    return productos


def ranking_repartidores():
    """Por repartidor, entregas con fin y minutos promedio, ordenado por
    entregas (mayor primero)."""
    from apps.entregas.models import Entrega

    resultado = []
    for repartidor in User.objects.filter(entregas__isnull=False).distinct():
        entregas_repartidor = Entrega.objects.filter(
            repartidor=repartidor, fin__isnull=False
        )
        total = entregas_repartidor.count()
        minutos = [
            e.minutos for e in entregas_repartidor if e.minutos is not None
        ]
        promedio = sum(minutos) / len(minutos) if minutos else 0
        resultado.append(
            {
                "repartidor": repartidor.username,
                "total_entregas": total,
                "minutos_promedio": round(promedio, 2),
            }
        )
    resultado.sort(key=lambda x: x["total_entregas"], reverse=True)
    return resultado
