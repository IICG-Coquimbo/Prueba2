from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, F, Sum
from django.utils import timezone

from apps.catalogo.models import OpcionProducto, Producto
from apps.cuentas.models import Direccion
from apps.entregas.models import Entrega
from apps.pagos.models import Pago
from apps.promociones.models import CodigoDescuento

from .models import HistorialEstado, ItemPedido, Pedido


Estado = Pedido.Estado
Metodo = Pedido.MetodoPago
TRANSICIONES = {
    Estado.CARRITO: (Estado.RECIBIDO, Estado.PENDIENTE_PAGO),
    Estado.PENDIENTE_PAGO: (Estado.RECIBIDO, Estado.CARRITO),
    Estado.RECIBIDO: (Estado.EN_PREPARACION,),
    Estado.EN_PREPARACION: (Estado.LISTO_DESPACHO,),
    Estado.LISTO_DESPACHO: (Estado.EN_CAMINO,),
    Estado.EN_CAMINO: (Estado.ENTREGADO,),
    Estado.ENTREGADO: (),
}
PERMISOS_AVANCE = {
    Estado.RECIBIDO: "pedidos.preparar_pedido",
    Estado.EN_PREPARACION: "pedidos.preparar_pedido",
    Estado.LISTO_DESPACHO: "pedidos.despachar_pedido",
    Estado.EN_CAMINO: "pedidos.despachar_pedido",
}
ESTADOS_VENTA = (
    Estado.RECIBIDO, Estado.EN_PREPARACION, Estado.LISTO_DESPACHO, Estado.EN_CAMINO, Estado.ENTREGADO
)
CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")


def _bloquear_pedido(pedido_id):
    try:
        return Pedido.objects.select_for_update(no_key=True).get(pk=pedido_id)
    except Pedido.DoesNotExist:
        raise ValidationError("El pedido no existe.") from None


def _exigir_carrito(pedido):
    if pedido.estado != Estado.CARRITO:
        raise ValidationError("Solo se puede modificar un pedido en estado carrito.")


def _validar_transicion(pedido, nuevo_estado):
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, ()):
        raise ValidationError("No se permite ese cambio desde el estado actual del pedido.")


def _importe(valor):
    importe = valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if abs(importe) >= Decimal("100000000"):
        raise ValidationError("El importe supera el máximo admitido.")
    return importe


@transaction.atomic
def obtener_carrito(usuario):
    """RF-04: devuelve el carrito del cliente o lo crea si no existe."""
    # Sin una restricción única parcial, se serializa la búsqueda/creación
    # por cliente. Si volvió un pago fallido, se retoma el carrito más antiguo.
    if not getattr(usuario, "is_authenticated", False) or not (
        get_user_model().objects.select_for_update(no_key=True).filter(pk=usuario.pk).exists()
    ):
        raise ValidationError("Necesitas una cuenta válida para obtener un carrito.")

    carrito = Pedido.objects.filter(cliente=usuario, estado=Estado.CARRITO).order_by("pk").first()
    if carrito is not None:
        return carrito
    return Pedido.objects.create(cliente=usuario)


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: agrega un artículo con sus variantes y precio actual."""
    actual = _bloquear_pedido(pedido.pk)
    _exigir_carrito(actual)
    if type(cantidad) is not int or not 1 <= cantidad <= 2147483647:
        raise ValidationError("La cantidad debe ser un entero positivo dentro del rango admitido.")

    producto = Producto.objects.select_for_update(no_key=True).filter(
        pk=getattr(producto, "pk", None), disponible=True
    ).first()
    if producto is None:
        raise ValidationError("El producto no está disponible.")

    # Los Select del formulario entregan instancias de OpcionProducto o None.
    seleccion = opciones.values() if isinstance(opciones, Mapping) else opciones
    try:
        elegidas = [opcion for opcion in (() if seleccion is None else seleccion) if opcion is not None]
    except TypeError:
        raise ValidationError("Elige opciones válidas para este producto.") from None
    if any(not isinstance(opcion, OpcionProducto) or opcion.pk is None for opcion in elegidas):
        raise ValidationError("Elige opciones válidas para este producto.")
    variantes = list(
        producto.opciones.select_for_update(no_key=True)
        .filter(pk__in=[opcion.pk for opcion in elegidas]).order_by("pk")
    )
    if {opcion.pk for opcion in variantes} != {opcion.pk for opcion in elegidas}:
        raise ValidationError("Todas las opciones deben pertenecer a este producto.")
    tipos = {opcion.tipo for opcion in variantes}
    if not tipos.issubset(OpcionProducto.Tipo.values):
        raise ValidationError("Una de las opciones tiene un tipo inválido.")
    if len(tipos) != len(elegidas):
        raise ValidationError("Elige como máximo una opción por tipo.")

    item = ItemPedido.objects.create(
        pedido=actual,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=_importe(producto.precio + sum((opcion.recargo for opcion in variantes), CERO)),
    )
    item.opciones.set(variantes)
    item.pedido = recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    """RF-04: elimina el artículo de un carrito y actualiza los importes."""
    pedido = _bloquear_pedido(item.pedido_id)
    _exigir_carrito(pedido)
    eliminados, _ = pedido.items.filter(pk=item.pk).delete()
    if not eliminados:
        raise ValidationError("El artículo no pertenece al carrito.")
    return recalcular_totales(pedido)


@transaction.atomic
def recalcular_totales(pedido):
    """RF-04, RF-16: calcula subtotal, descuento y total con dos decimales."""
    actual = _bloquear_pedido(pedido.pk)
    importes = actual.items.values_list("cantidad", "precio_unitario")
    subtotal = _importe(sum((cantidad * precio for cantidad, precio in importes), CERO))
    codigo = actual.codigo_descuento
    descuento = _importe(subtotal * codigo.porcentaje / Decimal("100")) if codigo else CERO
    actual.subtotal = subtotal
    actual.descuento = descuento
    actual.total = _importe(subtotal - descuento)
    actual.save(update_fields=["subtotal", "descuento", "total"])
    pedido.refresh_from_db()
    return pedido


@transaction.atomic
def aplicar_codigo(pedido, texto):
    """RF-16: aplica un código vigente y comprueba la condición de primer pedido."""
    actual = _bloquear_pedido(pedido.pk)
    _exigir_carrito(actual)
    if not isinstance(texto, str):
        raise ValidationError("Introduce un código de descuento válido.")
    codigo = CodigoDescuento.objects.filter(codigo=texto.strip(), activo=True).first()
    hoy = timezone.localdate()
    if codigo is None or not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El código no existe, está inactivo o no está vigente.")
    if codigo.solo_primer_pedido and Pedido.objects.filter(
        cliente_id=actual.cliente_id, estado__in=ESTADOS_VENTA
    ).exclude(pk=actual.pk).exists():
        raise ValidationError("Este código solo se puede usar en el primer pedido.")

    actual.codigo_descuento = codigo
    actual.save(update_fields=["codigo_descuento"])
    return recalcular_totales(pedido)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: confirma el carrito y devuelve el Pago del intento actual."""
    if metodo_pago not in Metodo.values:
        raise ValidationError("Elige efectivo o tarjeta como método de pago.")
    actual = _bloquear_pedido(pedido.pk)
    _exigir_carrito(actual)
    direccion = Direccion.objects.select_for_update(no_key=True).filter(
        pk=getattr(direccion, "pk", None), usuario_id=actual.cliente_id
    ).first()
    if direccion is None:
        raise ValidationError("Elige una dirección registrada en tu cuenta.")
    if not actual.items.exists():
        raise ValidationError("Agrega al menos un producto antes de confirmar el pedido.")

    pago = Pago.objects.select_for_update().filter(pedido=actual).first()
    if pago is not None and pago.estado != Pago.Estado.FALLIDO:
        raise ValidationError("El pedido ya tiene un pago pendiente o resuelto.")

    recalcular_totales(actual)
    actual.direccion = direccion
    actual.metodo_pago = metodo_pago
    actual.save(update_fields=["direccion", "metodo_pago"])

    referencia = str(uuid4())
    if pago is None:
        pago = Pago.objects.create(
            pedido=actual, metodo=metodo_pago, referencia=referencia, monto=actual.total
        )
    else:
        # OneToOne: reutilizar solo el intento fallido e invalidar su referencia.
        pago.metodo = metodo_pago
        pago.estado = Pago.Estado.PENDIENTE
        pago.referencia = referencia
        pago.monto = actual.total
        pago.fecha = timezone.now()
        pago.save(update_fields=["metodo", "estado", "referencia", "monto", "fecha"])

    siguiente = Estado.RECIBIDO if metodo_pago == Metodo.EFECTIVO else Estado.PENDIENTE_PAGO
    registrar_estado(actual, siguiente, usuario=actual.cliente)
    pedido.refresh_from_db()
    return pago


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: aplica la transición operativa según permiso y repartidor."""
    actual = _bloquear_pedido(pedido.pk)
    _validar_transicion(actual, nuevo_estado)
    permiso = PERMISOS_AVANCE.get(actual.estado)
    if not permiso or not getattr(usuario, "is_authenticated", False) or not usuario.has_perm(permiso):
        raise ValidationError("No tienes permiso para cambiar el pedido a ese estado.")

    if nuevo_estado == Estado.EN_CAMINO:
        if Entrega.objects.filter(pedido=actual).exists():
            raise ValidationError("Este pedido ya tiene una entrega asignada.")
        Entrega.objects.create(pedido=actual, repartidor=usuario, inicio=timezone.now())
    elif nuevo_estado == Estado.ENTREGADO:
        entrega = Entrega.objects.select_for_update().filter(pedido=actual).first()
        if entrega is None or entrega.repartidor_id != usuario.pk:
            raise ValidationError("Solo el repartidor asignado puede marcar el pedido como entregado.")
        if entrega.fin is not None:
            raise ValidationError("La entrega ya fue finalizada.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    return registrar_estado(pedido, nuevo_estado, usuario)


@transaction.atomic
def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RF-09, RNF-07: guarda una transición permitida y su historial atómico."""
    actual = _bloquear_pedido(pedido.pk)
    _validar_transicion(actual, nuevo_estado)
    actual.estado = nuevo_estado
    actual.save(update_fields=["estado"])
    historial = HistorialEstado.objects.create(pedido=actual, estado=nuevo_estado, usuario=usuario)
    pedido.refresh_from_db()
    return historial


def ventas_periodo(dias):
    """RF-17: devuelve el total vendido durante los últimos días locales (1 = hoy)."""
    if type(dias) is not int or dias < 1:
        raise ValidationError("El período debe ser de al menos un día entero.")
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=dias - 1)
    return Pedido.objects.filter(
        estado__in=ESTADOS_VENTA, creado__date__range=(desde, hoy)
    ).aggregate(ventas=Sum("total", default=CERO))["ventas"]


def productos_mas_pedidos(limite=5):
    """RF-17: devuelve filas con producto_id, producto__nombre y unidades vendidas."""
    if type(limite) is not int or limite < 0:
        raise ValidationError("El límite debe ser un entero no negativo.")
    return (
        ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENTA)
        .values("producto_id", "producto__nombre")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades", "producto_id")[:limite]
    )


def ranking_repartidores():
    """RF-18: devuelve entregas finalizadas y minutos promedio por repartidor."""
    filas = (
        Entrega.objects.filter(fin__isnull=False)
        .values("repartidor_id", "repartidor__username")
        .annotate(entregas=Count("pk"), duracion_promedio=Avg(F("fin") - F("inicio")))
        .order_by("-entregas", "repartidor_id")
    )
    return [
        {
            "repartidor_id": fila["repartidor_id"],
            "repartidor__username": fila["repartidor__username"],
            "entregas": fila["entregas"],
            "minutos_promedio": fila["duracion_promedio"].total_seconds() / 60,
        }
        for fila in filas
    ]
