import uuid
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Pedido, ItemPedido, HistorialEstado
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pagos.models import Pago
from apps.entregas.models import Entrega
from django.contrib.auth.models import User

TRANSICIONES = {
    "carrito": ["recibido"],
    "pendiente_pago": ["recibido", "carrito"],
    "recibido": ["en_preparacion"],
    "en_preparacion": ["listo_despacho"],
    "listo_despacho": ["en_camino"],
    "en_camino": ["entregado"],
    "entregado": [],
}


def obtener_carrito(usuario):
    pedido, _ = Pedido.objects.get_or_create(
        cliente=usuario, estado="carrito",
        defaults={"direccion": None, "metodo_pago": None, "codigo_descuento": None,
                  "subtotal": 0, "descuento": 0, "total": 0},
    )
    return pedido


def recalcular_totales(pedido):
    items = pedido.items.all()
    subtotal = sum((i.cantidad * i.precio_unitario for i in items), 0)
    descuento = 0
    if pedido.codigo_descuento_id:
        try:
            codigo = CodigoDescuento.objects.get(pk=pedido.codigo_descuento_id)
            descuento = subtotal * codigo.porcentaje / 100
        except CodigoDescuento.DoesNotExist:
            descuento = 0
    total = subtotal - descuento
    pedido.subtotal = round(subtotal, 2)
    pedido.descuento = round(descuento, 2)
    pedido.total = round(total, 2)
    pedido.save()


def agregar_item(pedido, producto, cantidad, opciones):
    if pedido.estado != "carrito":
        raise ValidationError("Solo se puede agregar al carrito.")
    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor a 0.")
    op_ids = [o.pk for o in opciones] if opciones else []
    op_qs = OpcionProducto.objects.filter(pk__in=op_ids, producto=producto)
    if op_qs.count() != len(op_ids):
        raise ValidationError("Opciones inválidas para este producto.")
    tipos = [o.tipo for o in op_qs]
    if len(tipos) != len(set(tipos)):
        raise ValidationError("Solo una opción por tipo.")
    recargo = sum((o.recargo for o in op_qs), 0)
    precio_unitario = producto.precio + recargo
    item = ItemPedido.objects.create(
        pedido=pedido, producto=producto, cantidad=cantidad,
        precio_unitario=precio_unitario,
    )
    item.opciones.set(op_qs)
    recalcular_totales(pedido)
    return item


def quitar_item(item):
    if item.pedido.estado != "carrito":
        raise ValidationError("Solo se puede quitar del carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)


def aplicar_codigo(pedido, texto):
    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("Codigo de descuento no existe.")
    if not codigo.activo:
        raise ValidationError("El codigo no esta activo.")
    hoy = timezone.localdate()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("El codigo no esta vigente.")
    if codigo.solo_primer_pedido:
        tiene_otros = Pedido.objects.filter(
            cliente=pedido.cliente
        ).exclude(estado__in=["carrito", "pendiente_pago"]).exists()
        if tiene_otros:
            raise ValidationError("Este codigo es solo para el primer pedido.")
    pedido.codigo_descuento = codigo
    recalcular_totales(pedido)


def registrar_estado(pedido, nuevo_estado, usuario=None):
    pedido.estado = nuevo_estado
    pedido.save()
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != "carrito":
        raise ValidationError("Solo se puede confirmar un carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito esta vacio.")
    if not direccion or direccion.cliente != pedido.cliente:
        raise ValidationError("Direccion invalida.")
    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pago = Pago.objects.create(
        pedido=pedido, metodo=metodo_pago, estado="pendiente",
        referencia=str(uuid.uuid4()), monto=pedido.total,
    )
    if metodo_pago == "efectivo":
        registrar_estado(pedido, "recibido")
    else:
        registrar_estado(pedido, "pendiente_pago")
    return pago


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    actual = pedido.estado
    if nuevo_estado not in TRANSICIONES.get(actual, []):
        raise ValidationError(f"No se puede pasar de {actual} a {nuevo_estado}.")
    user = usuario
    if user.groups.filter(name="Barista").exists():
        if actual == "recibido" and nuevo_estado != "en_preparacion":
            raise ValidationError("El barista solo puede preparar.")
        if actual == "en_preparacion" and nuevo_estado != "listo_despacho":
            raise ValidationError("El barista solo puede listar para despacho.")
    elif user.groups.filter(name="Repartidor").exists():
        if actual == "listo_despacho" and nuevo_estado != "en_camino":
            raise ValidationError("El repartidor solo puede enviar a camino.")
        if actual == "en_camino":
            try:
                entrega = pedido.entrega
                if entrega.repartidor != user:
                    raise ValidationError("No eres el repartidor de esta entrega.")
            except Entrega.DoesNotExist:
                raise ValidationError("No hay entrega asignada.")
            if nuevo_estado != "entregado":
                raise ValidationError("El repartidor solo puede entregar.")
    else:
        raise ValidationError("Rol no autorizado para este cambio.")
    registrar_estado(pedido, nuevo_estado, usuario)
    if nuevo_estado == "en_camino":
        Entrega.objects.create(pedido=pedido, repartidor=user, inicio=timezone.now())


def ventas_periodo(dias):
    desde = timezone.now() - timezone.timedelta(days=dias)
    total = Pedido.objects.filter(
        estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"],
        creado__gte=desde,
    ).aggregate(s=Sum("total"))["s"] or 0
    return total


def productos_mas_pedidos(limite=5):
    return (
        ItemPedido.objects.filter(
            pedido__estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"]
        )
        .values("producto__nombre")
        .annotate(total_cantidad=Sum("cantidad"))
        .order_by("-total_cantidad")[:limite]
    )


def ranking_repartidores():
    from django.db.models import Avg, Count
    return (
        Entrega.objects.filter(fin__isnull=False)
        .values("repartidor__username")
        .annotate(
            entregas=Count("id"),
            minutos_promedio=Avg(
                F("fin") - F("inicio")
            ),
        )
        .order_by("-entregas")
    )
