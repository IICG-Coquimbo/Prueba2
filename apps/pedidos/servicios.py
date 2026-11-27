import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Count

from .models import Pedido, ItemPedido, HistorialEstado
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.cuentas.models import Direccion
from apps.entregas.models import Entrega
from django.contrib.auth.models import User


TRANSICIONES = {
    "carrito": ["recibido", "pendiente_pago"],
    "pendiente_pago": ["recibido", "carrito"],
    "recibido": ["en_preparacion"],
    "en_preparacion": ["listo_despacho"],
    "listo_despacho": ["en_camino"],
    "en_camino": ["entregado"],
    "entregado": [],
}


def obtener_carrito(usuario):
    """Devuelve el pedido en estado carrito del usuario; si no existe, lo crea."""
    carrito = Pedido.objects.filter(cliente=usuario, estado="carrito").first()
    if not carrito:
        carrito = Pedido.objects.create(cliente=usuario, estado="carrito")
    return carrito


def recalcular_totales(pedido):
    """Recalcula subtotal, descuento y total del pedido."""
    items = pedido.items.all()
    subtotal = sum((item.cantidad * item.precio_unitario for item in items), 0)
    descuento = 0
    if pedido.codigo_descuento:
        descuento = subtotal * pedido.codigo_descuento.porcentaje / 100
    total = subtotal - descuento
    pedido.subtotal = round(subtotal, 2)
    pedido.descuento = round(descuento, 2)
    pedido.total = round(total, 2)
    pedido.save()


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """Cambia el estado del pedido y crea una entrada en HistorialEstado."""
    pedido.estado = nuevo_estado
    pedido.save()
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones):
    """Agrega un producto al carrito con sus opciones."""
    if pedido.estado != "carrito":
        raise ValidationError("Solo se puede agregar items a un carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    # Validar opciones: pertenecen al producto y máximo una por tipo
    tipos_vistos = set()
    opcion_objs = []
    for opcion_id in opciones:
        try:
            opcion = OpcionProducto.objects.get(id=opcion_id, producto=producto)
        except OpcionProducto.DoesNotExist:
            raise ValidationError(f"La opcion {opcion_id} no pertenece al producto.")
        if opcion.tipo in tipos_vistos:
            raise ValidationError(f"Solo se permite una opcion por tipo ({opcion.tipo}).")
        tipos_vistos.add(opcion.tipo)
        opcion_objs.append(opcion)

    # Calcular precio unitario
    recargos = sum((o.recargo for o in opcion_objs), 0)
    precio_unitario = producto.precio + recargos

    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(opcion_objs)
    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    """Quita un item del carrito."""
    pedido = item.pedido
    if pedido.estado != "carrito":
        raise ValidationError("Solo se puede quitar items de un carrito.")
    item.delete()
    recalcular_totales(pedido)


@transaction.atomic
def aplicar_codigo(pedido, texto):
    """Aplica un codigo de descuento al pedido."""
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El codigo de descuento no existe.")

    hoy = timezone.now().date()
    if not codigo.activo:
        raise ValidationError("El codigo de descuento no esta activo.")
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El codigo de descuento no esta vigente.")

    if codigo.solo_primer_pedido:
        tiene_otros = Pedido.objects.filter(
            cliente=pedido.cliente
        ).exclude(
            estado__in=["carrito", "pendiente_pago"]
        ).exists()
        if tiene_otros:
            raise ValidationError("Este codigo es solo para el primer pedido.")

    pedido.codigo_descuento = codigo
    pedido.save()
    recalcular_totales(pedido)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    """Confirma el pedido: crea el Pago y cambia el estado según el metodo."""
    from apps.pagos.models import Pago

    if pedido.estado != "carrito":
        raise ValidationError("El pedido debe estar en estado carrito para confirmar.")
    if not pedido.items.exists():
        raise ValidationError("El carrito debe tener al menos un item.")
    if not direccion or direccion.usuario != pedido.cliente:
        raise ValidationError("La direccion debe pertenecer al cliente.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save()

    pago = Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        estado="pendiente",
        referencia=str(uuid.uuid4()),
        monto=pedido.total,
    )

    if metodo_pago == "efectivo":
        registrar_estado(pedido, "recibido")
    else:
        registrar_estado(pedido, "pendiente_pago")

    return pago


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """Avanza el estado del pedido validando transiciones y roles."""
    estado_actual = pedido.estado
    estados_permitidos = TRANSICIONES.get(estado_actual, [])
    if nuevo_estado not in estados_permitidos:
        raise ValidationError(f"No se puede pasar de {estado_actual} a {nuevo_estado}.")

    # Validar por rol
    es_barista = usuario.has_perm("pedidos.preparar_pedido")
    es_despachador = usuario.has_perm("pedidos.despachar_pedido")

    if nuevo_estado in ["en_preparacion", "listo_despacho"]:
        if not es_barista:
            raise ValidationError("No tienes permiso para preparar pedidos.")
    elif nuevo_estado in ["en_camino", "entregado"]:
        if not es_despachador:
            raise ValidationError("No tienes permiso para despachar pedidos.")
        if nuevo_estado == "en_camino":
            # Crear Entrega
            Entrega.objects.create(
                pedido=pedido,
                repartidor=usuario,
                inicio=timezone.now(),
            )
        elif nuevo_estado == "entregado":
            # Solo el repartidor de la Entrega puede entregar
            try:
                entrega = pedido.entrega
                if entrega.repartidor != usuario:
                    raise ValidationError("Solo el repartidor asignado puede marcar como entregado.")
                entrega.fin = timezone.now()
                entrega.save()
            except Entrega.DoesNotExist:
                raise ValidationError("No hay entrega asociada a este pedido.")

    registrar_estado(pedido, nuevo_estado, usuario=usuario)


def ventas_periodo(dias):
    """Suma del total de pedidos en estado recibido o posterior en los últimos <dias> días."""
    desde = timezone.now() - timezone.timedelta(days=dias)
    pedidos = Pedido.objects.filter(
        estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"],
        creado__gte=desde,
    )
    total = pedidos.aggregate(total=Sum("total"))["total"] or 0
    return total


def productos_mas_pedidos(limite=5):
    """Productos con más unidades en pedidos recibidos o posteriores."""
    from apps.catalogo.models import Producto
    productos = Producto.objects.filter(
        items__pedido__estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"]
    ).annotate(
        total_unidades=Sum("items__cantidad")
    ).order_by("-total_unidades")[:limite]
    return productos


def ranking_repartidores():
    """Por repartidor, entregas con fin y minutos promedio, ordenado por entregas."""
    from django.contrib.auth.models import User
    repartidores = User.objects.filter(
        entregas__fin__isnull=False
    ).annotate(
        total_entregas=Count("entregas"),
    ).order_by("-total_entregas")
    return repartidores
