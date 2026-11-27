from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import OpcionProducto, Producto
from apps.cuentas.models import Direccion
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido


CENTAVOS = Decimal("0.01")
CERO = Decimal("0.00")
TIPOS_OPCION = {tipo for tipo, _etiqueta in OpcionProducto.Tipo.choices}
ESTADOS_POSTERIORES = [
    Pedido.Estado.RECIBIDO,
    Pedido.Estado.EN_PREPARACION,
    Pedido.Estado.LISTO_DESPACHO,
    Pedido.Estado.EN_CAMINO,
    Pedido.Estado.ENTREGADO,
]
TRANSICIONES = {
    Pedido.Estado.CARRITO: [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO],
    Pedido.Estado.PENDIENTE_PAGO: [Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO],
    Pedido.Estado.RECIBIDO: [Pedido.Estado.EN_PREPARACION],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.LISTO_DESPACHO],
    Pedido.Estado.LISTO_DESPACHO: [Pedido.Estado.EN_CAMINO],
    Pedido.Estado.EN_CAMINO: [Pedido.Estado.ENTREGADO],
    Pedido.Estado.ENTREGADO: [],
}
PERMISO_PREPARAR = "pedidos.preparar_pedido"
PERMISO_DESPACHAR = "pedidos.despachar_pedido"


def _dos_decimales(valor):
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def obtener_carrito(usuario):
    pedido, _creado = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=Pedido.Estado.CARRITO,
        defaults={"subtotal": CERO, "descuento": CERO, "total": CERO},
    )
    return pedido


def recalcular_totales(pedido):
    subtotal = CERO
    for item in pedido.items.all():
        subtotal += Decimal(item.cantidad) * item.precio_unitario
    subtotal = _dos_decimales(subtotal)
    descuento = CERO
    if pedido.codigo_descuento_id:
        porcentaje = Decimal(pedido.codigo_descuento.porcentaje)
        descuento = _dos_decimales(subtotal * porcentaje / Decimal("100"))
    total = _dos_decimales(subtotal - descuento)
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])
    return pedido


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden agregar items a un pedido en carrito.")
    if not isinstance(producto, Producto):
        producto = Producto.objects.get(pk=producto)
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        raise ValidationError("La cantidad debe ser mayor que 0.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")
    opciones = list(opciones or [])
    opciones_validadas = []
    for opcion in opciones:
        if not isinstance(opcion, OpcionProducto):
            opcion = OpcionProducto.objects.get(pk=opcion)
        if opcion.producto_id != producto.pk:
            raise ValidationError("La opción no pertenece al producto.")
        opciones_validadas.append(opcion)
    tipos = [opcion.tipo for opcion in opciones_validadas]
    if len(tipos) != len(set(tipos)):
        raise ValidationError("Como máximo una opción por tipo.")
    if set(tipos) - TIPOS_OPCION:
        raise ValidationError("Tipo de opción no válido.")
    precio_unitario = _dos_decimales(producto.precio + sum((opcion.recargo for opcion in opciones_validadas), CERO))
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(opciones_validadas)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    pedido = item.pedido
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden quitar items de un pedido en carrito.")
    item.delete()
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede aplicar código a un pedido en carrito.")
    texto = (texto or "").strip()
    try:
        codigo = CodigoDescuento.objects.get(codigo__iexact=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("Código no encontrado.")
    hoy = timezone.localdate()
    if not codigo.activo:
        raise ValidationError("El código no está activo.")
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código no está vigente.")
    if not (1 <= codigo.porcentaje <= 100):
        raise ValidationError("Porcentaje no válido.")
    if codigo.solo_primer_pedido:
        tiene_otro_pedido = Pedido.objects.filter(cliente=pedido.cliente).exclude(pk=pedido.pk).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]).exists()
        if tiene_otro_pedido:
            raise ValidationError("El código solo aplica al primer pedido.")
    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)
    return pedido


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("El pedido no está en carrito.")
    if not pedido.items.exists():
        raise ValidationError("El pedido debe tener al menos un item.")
    if not isinstance(direccion, Direccion):
        direccion = Direccion.objects.get(pk=direccion)
    if direccion.usuario_id != pedido.cliente_id:
        raise ValidationError("La dirección debe ser del mismo cliente.")
    if metodo_pago not in Pedido.MetodoPago.values:
        raise ValidationError("Método de pago no válido.")
    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])
    recalcular_totales(pedido)
    Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado=Pago.Estado.PENDIENTE,
        referencia=str(uuid4()),
        monto=pedido.total,
    )
    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO, usuario=pedido.cliente)
    else:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO, usuario=pedido.cliente)
    pedido.refresh_from_db()
    return pedido


@transaction.atomic
def registrar_estado(pedido, nuevo_estado, usuario=None):
    if nuevo_estado not in Pedido.Estado.values:
        raise ValidationError("Estado no válido.")
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)
    return pedido


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    estado_actual = pedido.estado
    if nuevo_estado not in TRANSICIONES.get(estado_actual, []):
        raise ValidationError("Transición no permitida.")
    if usuario is None or not usuario.is_authenticated:
        raise ValidationError("Usuario no autenticado.")
    if nuevo_estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
        if not usuario.has_perm(PERMISO_PREPARAR):
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif nuevo_estado in [Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]:
        if not usuario.has_perm(PERMISO_DESPACHAR):
            raise ValidationError("No tienes permiso para despachar pedidos.")
    if nuevo_estado == Pedido.Estado.EN_CAMINO:
        Entrega.objects.create(pedido=pedido, repartidor=usuario, inicio=timezone.now())
    if nuevo_estado == Pedido.Estado.ENTREGADO:
        entrega = Entrega.objects.get(pedido=pedido)
        if entrega.repartidor_id != usuario.id:
            raise ValidationError("Solo el repartidor de la entrega puede marcar entregado.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])
    registrar_estado(pedido, nuevo_estado, usuario=usuario)
    return pedido
