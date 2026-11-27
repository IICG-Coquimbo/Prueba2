import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido


TRANSICIONES = {
    'carrito': {'recibido', 'pendiente_pago'},
    'pendiente_pago': {'recibido', 'carrito'},
    'recibido': {'en_preparacion'},
    'en_preparacion': {'listo_despacho'},
    'listo_despacho': {'en_camino'},
    'en_camino': {'entregado'},
    'entregado': set(),
}

ESTADOS_POSTERIORES = (
    'recibido',
    'en_preparacion',
    'listo_despacho',
    'en_camino',
    'entregado',
)


def obtener_carrito(usuario):
    """RF-04: devuelve el pedido en carrito del usuario y lo crea si no existe."""
    with transaction.atomic():
        pedido = Pedido.objects.filter(cliente=usuario, estado='carrito').first()
        if pedido is None:
            pedido = Pedido.objects.create(cliente=usuario, estado='carrito')
    return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: agrega un item al carrito calculando su precio unitario."""
    if pedido.estado != 'carrito':
        raise ValidationError('El pedido debe estar en carrito para agregar productos.')
    if not producto.disponible:
        raise ValidationError('El producto no está disponible.')
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValidationError('La cantidad debe ser mayor que cero.')
    if cantidad <= 0:
        raise ValidationError('La cantidad debe ser mayor que cero.')

    opciones = list(opciones or [])
    seleccionadas = []
    tipos_vistos = set()
    with transaction.atomic():
        for opcion in opciones:
            if not isinstance(opcion, OpcionProducto):
                try:
                    opcion = OpcionProducto.objects.get(pk=opcion)
                except (OpcionProducto.DoesNotExist, ValueError, TypeError):
                    raise ValidationError('Las opciones seleccionadas no son válidas.')
            if opcion.producto_id != producto.pk:
                raise ValidationError(
                    'Las opciones deben pertenecer al producto seleccionado.'
                )
            if opcion.tipo in tipos_vistos:
                raise ValidationError(
                    'Solo se permite una opción por tipo (tamano, leche, azucar).'
                )
            tipos_vistos.add(opcion.tipo)
            seleccionadas.append(opcion)

        recargos = sum(
            (Decimal(str(opcion.recargo)) for opcion in seleccionadas),
            Decimal('0.00'),
        )
        precio_unitario = (
            Decimal(str(producto.precio)) + recargos
        ).quantize(Decimal('0.01'))
        item = ItemPedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
        )
        if seleccionadas:
            item.opciones.set(seleccionadas)
        recalcular_totales(pedido)
    return item


def quitar_item(item):
    """RF-04: quita un item del carrito y recalcula los totales del pedido."""
    pedido = item.pedido
    if pedido.estado != 'carrito':
        raise ValidationError('El pedido debe estar en carrito para quitar productos.')
    with transaction.atomic():
        pedido.save()
        item.delete()
        recalcular_totales(pedido)


def recalcular_totales(pedido):
    """RF-04/RF-16: recalcula subtotal, descuento y total con dos decimales."""
    with transaction.atomic():
        subtotal = sum(
            (
                Decimal(str(item.cantidad)) * Decimal(str(item.precio_unitario))
                for item in pedido.items.all()
            ),
            Decimal('0.00'),
        ).quantize(Decimal('0.01'))

        descuento = Decimal('0.00')
        if pedido.codigo_descuento_id is not None:
            porcentaje = Decimal(str(pedido.codigo_descuento.porcentaje))
            descuento = (subtotal * porcentaje / Decimal('100')).quantize(
                Decimal('0.01')
            )

        total = (subtotal - descuento).quantize(Decimal('0.01'))
        pedido.subtotal = subtotal
        pedido.descuento = descuento
        pedido.total = total
        pedido.save()
    return pedido


def aplicar_codigo(pedido, texto):
    """RF-16: valida y aplica un código de descuento al pedido."""
    codigo_texto = (texto or '').strip().upper()
    if not codigo_texto:
        raise ValidationError('Debe ingresar un código de descuento.')

    with transaction.atomic():
        codigo = CodigoDescuento.objects.filter(codigo=codigo_texto).first()
        if codigo is None:
            raise ValidationError('El código de descuento no existe.')
        if not codigo.activo:
            raise ValidationError('El código de descuento no está activo.')

        hoy = timezone.localdate()
        if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
            raise ValidationError('El código de descuento no está vigente.')

        if codigo.solo_primer_pedido:
            anteriores = Pedido.objects.filter(cliente=pedido.cliente).exclude(
                estado__in=['carrito', 'pendiente_pago']
            )
            if pedido.pk is not None:
                anteriores = anteriores.exclude(pk=pedido.pk)
            if anteriores.exists():
                raise ValidationError(
                    'Este código solo se puede usar en el primer pedido.'
                )

        pedido.codigo_descuento = codigo
        recalcular_totales(pedido)
    return pedido


def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: confirma el carrito, crea el pago y registra el nuevo estado."""
    if pedido.estado != 'carrito':
        raise ValidationError('El pedido debe estar en carrito para confirmarlo.')
    if not pedido.items.exists():
        raise ValidationError('El pedido debe tener al menos un item.')
    if metodo_pago not in ('efectivo', 'tarjeta'):
        raise ValidationError('El método de pago no es válido.')

    with transaction.atomic():
        if not isinstance(direccion, Direccion):
            try:
                direccion = Direccion.objects.get(pk=direccion)
            except (Direccion.DoesNotExist, ValueError, TypeError):
                raise ValidationError('La dirección no es válida.')
        if direccion.usuario_id != pedido.cliente_id:
            raise ValidationError('La dirección no pertenece al cliente del pedido.')

        Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado='pendiente',
            referencia=str(uuid.uuid4()),
            monto=Decimal(str(pedido.total)).quantize(Decimal('0.01')),
        )
        pedido.direccion = direccion
        pedido.metodo_pago = metodo_pago

        if metodo_pago == 'efectivo':
            registrar_estado(pedido, 'recibido')
        else:
            registrar_estado(pedido, 'pendiente_pago')
    return pedido


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: avanza el pedido validando la transición y el permiso del usuario."""
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, set()):
        raise ValidationError('Transición de estado no permitida.')

    transicion = (pedido.estado, nuevo_estado)
    preparando = transicion in (
        ('recibido', 'en_preparacion'),
        ('en_preparacion', 'listo_despacho'),
    )
    despachando = transicion in (
        ('listo_despacho', 'en_camino'),
        ('en_camino', 'entregado'),
    )
    if not preparando and not despachando:
        raise ValidationError('Transición de estado no permitida.')
    if usuario is None:
        raise ValidationError('Se requiere un usuario para avanzar el pedido.')

    with transaction.atomic():
        if preparando:
            if not usuario.has_perm('pedidos.preparar_pedido'):
                raise ValidationError('No tiene permiso para preparar pedidos.')
        else:
            if not usuario.has_perm('pedidos.despachar_pedido'):
                raise ValidationError('No tiene permiso para despachar pedidos.')
            if nuevo_estado == 'en_camino':
                Entrega.objects.create(
                    pedido=pedido,
                    repartidor=usuario,
                    inicio=timezone.now(),
                )
            else:
                entrega = Entrega.objects.filter(pedido=pedido).first()
                if entrega is None or entrega.repartidor_id != usuario.pk:
                    raise ValidationError(
                        'Solo el repartidor asignado puede marcar la entrega como entregada.'
                    )
                entrega.fin = timezone.now()
                entrega.save(update_fields=['fin'])

        registrar_estado(pedido, nuevo_estado, usuario)
    return pedido


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RNF-07: cambia el estado del pedido y deja constancia en el historial."""
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, set()):
        raise ValidationError('Transición de estado no permitida.')

    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save()
        historial = HistorialEstado.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            usuario=usuario,
        )
    return historial


def ventas_periodo(dias):
    """RF-17: suma las ventas de los últimos días, contando hoy como el primero."""
    try:
        dias = int(dias)
    except (TypeError, ValueError):
        raise ValidationError('El número de días debe ser mayor que cero.')
    if dias <= 0:
        raise ValidationError('El número de días debe ser mayor que cero.')

    desde = timezone.localdate() - timedelta(days=dias - 1)
    total = Pedido.objects.filter(
        estado__in=ESTADOS_POSTERIORES,
        creado__date__gte=desde,
    ).aggregate(total=Sum('total'))['total']
    total = Decimal(str(total)) if total is not None else Decimal('0.00')
    return total.quantize(Decimal('0.01'))


def productos_mas_pedidos(limite=5):
    """RF-17: devuelve los productos más pedidos con sus unidades vendidas."""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        raise ValidationError('El límite debe ser un número entero.')
    if limite <= 0:
        return []

    with transaction.atomic():
        filas = (
            ItemPedido.objects.filter(pedido__estado__in=ESTADOS_POSTERIORES)
            .values('producto_id', 'producto__nombre')
            .annotate(unidades=Sum('cantidad'))
            .order_by('-unidades')[:limite]
        )
        return [
            {'nombre': fila['producto__nombre'], 'unidades': fila['unidades']}
            for fila in filas
        ]


def ranking_repartidores():
    """RF-18: ranking de repartidores por entregas finalizadas y minutos promedio."""
    with transaction.atomic():
        agrupado = {}
        entregas = Entrega.objects.filter(fin__isnull=False).select_related(
            'repartidor'
        )
        for entrega in entregas:
            datos = agrupado.setdefault(
                entrega.repartidor,
                {'entregas': 0, 'minutos': Decimal('0')},
            )
            datos['entregas'] += 1
            minutos = entrega.minutos
            if minutos is not None:
                datos['minutos'] += Decimal(str(minutos))

        resultado = [
            {
                'repartidor': repartidor,
                'entregas': datos['entregas'],
                'minutos_promedio': (
                    datos['minutos'] / Decimal(datos['entregas'])
                ).quantize(Decimal('0.01')),
            }
            for repartidor, datos in agrupado.items()
        ]

    resultado.sort(key=lambda fila: fila['entregas'], reverse=True)
    return resultado
