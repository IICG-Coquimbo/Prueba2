from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, DurationField, ExpressionWrapper, Q
import uuid

from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pagos.models import Pago
from apps.entregas.models import Entrega
from django.contrib.auth.models import User


# RF-12, RF-14: TRANSICIONES de estado permitidas
TRANSICIONES = {
    Pedido.Estado.CARRITO: [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO],
    Pedido.Estado.PENDIENTE_PAGO: [Pedido.Estado.CARRITO, Pedido.Estado.RECIBIDO],
    Pedido.Estado.RECIBIDO: [Pedido.Estado.EN_PREPARACION],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.LISTO_DESPACHO],
    Pedido.Estado.LISTO_DESPACHO: [Pedido.Estado.EN_CAMINO],
    Pedido.Estado.EN_CAMINO: [Pedido.Estado.ENTREGADO],
    Pedido.Estado.ENTREGADO: [],
}


def obtener_carrito(usuario):
    """
    RF-04: Devuelve el pedido en estado carrito del usuario; si no existe, lo crea.
    Retorna (pedido, created).
    """
    pedido, created = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=Pedido.Estado.CARRITO,
        defaults={'subtotal': Decimal('0'), 'descuento': Decimal('0'), 'total': Decimal('0')}
    )
    return pedido, created


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    """
    RF-04, RF-05, RF-15: Agrega un item al pedido (carrito).
    Valida: pedido en carrito, producto disponible, cantidad > 0,
    opciones pertenecen al producto y máximo 1 por tipo.
    Calcula precio_unitario = precio + recargos. Llama a recalcular_totales.
    """
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un carrito.")

    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")

    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    # Validar opciones: pertenecen al producto y máximo 1 por tipo
    opciones = list(opciones)
    tipos_vistos = set()
    for opcion in opciones:
        if opcion.producto_id != producto.id:
            raise ValidationError(f"La opción '{opcion.nombre}' no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError(f"Solo se permite una opción de tipo '{opcion.get_tipo_display()}'.")
        tipos_vistos.add(opcion.tipo)

    # Calcular precio unitario
    precio_unitario = producto.precio + sum(opcion.recargo for opcion in opciones)

    # Crear ItemPedido
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario
    )
    if opciones:
        item.opciones.set(opciones)

    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    """
    RF-04: Quita un item del carrito. Valida estado carrito.
    Llama a recalcular_totales.
    """
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden quitar items de un carrito.")

    item.delete()
    recalcular_totales(pedido)


def recalcular_totales(pedido):
    """
    RF-04, RF-16: Recalcula subtotal, descuento y total del pedido.
    subtotal = suma(cantidad * precio_unitario)
    descuento = subtotal * porcentaje / 100 si hay código, else 0
    total = subtotal - descuento (2 decimales)
    """
    subtotal = sum(
        Decimal(item.cantidad) * item.precio_unitario
        for item in pedido.items.all()
    )

    descuento = Decimal('0')
    if pedido.codigo_descuento:
        descuento = (subtotal * Decimal(pedido.codigo_descuento.porcentaje) / Decimal('100')).quantize(Decimal('0.01'))

    total = (subtotal - descuento).quantize(Decimal('0.01'))

    pedido.subtotal = subtotal.quantize(Decimal('0.01'))
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=['subtotal', 'descuento', 'total'])


@transaction.atomic
def aplicar_codigo(pedido, texto):
    """
    RF-16: Aplica un código de descuento al pedido.
    Valida: código existe, activo, fecha vigente, y si solo_primer_pedido
    que el cliente no tenga pedidos en estados post-carrito.
    Guarda el código y recalcula totales.
    """
    try:
        codigo = CodigoDescuento.objects.get(codigo__iexact=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El código de descuento no existe.")

    hoy = timezone.now().date()
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código de descuento no está vigente.")

    if codigo.solo_primer_pedido:
        # Verificar si el cliente tiene pedidos en estados post-carrito
        estados_post = [
            Pedido.Estado.RECIBIDO,
            Pedido.Estado.EN_PREPARACION,
            Pedido.Estado.LISTO_DESPACHO,
            Pedido.Estado.EN_CAMINO,
            Pedido.Estado.ENTREGADO,
        ]
        tiene_pedidos = Pedido.objects.filter(
            cliente=pedido.cliente,
            estado__in=estados_post
        ).exists()
        if tiene_pedidos:
            raise ValidationError("Este código solo es válido para el primer pedido.")

    pedido.codigo_descuento = codigo
    pedido.save(update_fields=['codigo_descuento'])
    recalcular_totales(pedido)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    """
    RF-07: Confirma el pedido creando el Pago.
    Valida: estado carrito, al menos un item, dirección del mismo cliente.
    Crea Pago con estado pendiente, referencia uuid, monto = total.
    Efectivo -> registrar_estado(recibido)
    Tarjeta -> registrar_estado(pendiente_pago)
    """
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede confirmar un carrito.")

    if not pedido.items.exists():
        raise ValidationError("El carrito está vacío.")

    if direccion.usuario != pedido.cliente:
        raise ValidationError("La dirección no pertenece al cliente.")

    # Crear Pago
    referencia = uuid.uuid4().hex
    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=Pago.Estado.PENDIENTE,
        referencia=referencia,
        monto=pedido.total,
        fecha=timezone.now()
    )

    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO)
    elif metodo_pago == Pedido.MetodoPago.TARJETA:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO)

    return pago


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    """
    RF-12, RF-14: Avanza el estado del pedido validando TRANSICIONES y permisos por rol.
    preparar_pedido: recibido->en_preparacion, en_preparacion->listo_despacho
    despachar_pedido: listo_despacho->en_camino (crea Entrega), en_camino->entregado (solo su repartidor)
    """
    # Validar transición permitida
    estados_permitidos = TRANSICIONES.get(pedido.estado, [])
    if nuevo_estado not in estados_permitidos:
        raise ValidationError(f"No se puede cambiar de '{pedido.get_estado_display()}' a '{dict(Pedido.Estado.choices).get(nuevo_estado, nuevo_estado)}'.")

    # Validar permisos por rol
    if not usuario.has_perm('pedidos.preparar_pedido') and not usuario.has_perm('pedidos.despachar_pedido'):
        raise ValidationError("El usuario no tiene permisos para cambiar el estado del pedido.")

    # Transiciones de preparar_pedido
    if nuevo_estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
        if not usuario.has_perm('pedidos.preparar_pedido'):
            raise ValidationError("No tiene permiso para preparar pedidos.")

    # Transiciones de despachar_pedido
    if nuevo_estado == Pedido.Estado.EN_CAMINO:
        if not usuario.has_perm('pedidos.despachar_pedido'):
            raise ValidationError("No tiene permiso para despachar pedidos.")
        # Crear Entrega con repartidor=usuario, inicio=now
        Entrega.objects.create(
            pedido=pedido,
            repartidor=usuario,
            inicio=timezone.now()
        )

    if nuevo_estado == Pedido.Estado.ENTREGADO:
        if not usuario.has_perm('pedidos.despachar_pedido'):
            raise ValidationError("No tiene permiso para entregar pedidos.")
        # Solo el repartidor de la entrega puede marcar como entregado
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("No hay entrega asociada a este pedido.")
        if entrega.repartidor != usuario:
            raise ValidationError("Solo el repartidor asignado puede marcar el pedido como entregado.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=['fin'])

    registrar_estado(pedido, nuevo_estado, usuario)


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """
    RNF-07: Cambia el estado del pedido y crea fila en HistorialEstado.
    """
    pedido.estado = nuevo_estado
    pedido.save(update_fields=['estado'])
    HistorialEstado.objects.create(
        pedido=pedido,
        estado=nuevo_estado,
        usuario=usuario
    )


def ventas_periodo(dias):
    """
    RF-17: Suma del total de pedidos en estado recibido o posterior
    creados en los últimos <dias> días (1 = hoy).
    """
    fecha_limite = timezone.now() - timezone.timedelta(days=dias)
    estados_validos = [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
        Pedido.Estado.EN_CAMINO,
        Pedido.Estado.ENTREGADO,
    ]
    total = Pedido.objects.filter(
        estado__in=estados_validos,
        creado__gte=fecha_limite
    ).aggregate(total=Sum('total'))['total']
    return total or Decimal('0')


def productos_mas_pedidos(limite=5):
    """
    RF-17: Productos con más unidades en pedidos recibidos o posteriores.
    """
    estados_validos = [
        Pedido.Estado.RECIBIDO,
        Pedido.Estado.EN_PREPARACION,
        Pedido.Estado.LISTO_DESPACHO,
        Pedido.Estado.EN_CAMINO,
        Pedido.Estado.ENTREGADO,
    ]
    return Producto.objects.filter(
        items__pedido__estado__in=estados_validos
    ).annotate(
        total_unidades=Sum('items__cantidad')
    ).order_by('-total_unidades')[:limite]


def ranking_repartidores():
    """
    RF-18: Por repartidor, entregas con fin y minutos promedio,
    ordenado por entregas (mayor primero).
    """
    from django.db.models import DurationField, ExpressionWrapper, F
    return Entrega.objects.filter(
        fin__isnull=False
    ).values('repartidor__username').annotate(
        total=Count('id'),
        min_prom=Avg(
            ExpressionWrapper(F('fin') - F('inicio'), output_field=DurationField())
        )
    ).order_by('-total')