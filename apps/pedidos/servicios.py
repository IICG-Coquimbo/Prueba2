from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento


TRANSICIONES = {
    Pedido.Estado.CARRITO: [Pedido.Estado.RECIBIDO, Pedido.Estado.PENDIENTE_PAGO],
    Pedido.Estado.PENDIENTE_PAGO: [Pedido.Estado.RECIBIDO, Pedido.Estado.CARRITO],
    Pedido.Estado.RECIBIDO: [Pedido.Estado.EN_PREPARACION],
    Pedido.Estado.EN_PREPARACION: [Pedido.Estado.LISTO_DESPACHO],
    Pedido.Estado.LISTO_DESPACHO: [Pedido.Estado.EN_CAMINO],
    Pedido.Estado.EN_CAMINO: [Pedido.Estado.ENTREGADO],
    Pedido.Estado.ENTREGADO: [],
}


@transaction.atomic
def obtener_carrito(usuario):
    carrito, _ = Pedido.objects.get_or_create(
        cliente=usuario,
        estado=Pedido.Estado.CARRITO,
        defaults={"subtotal": 0, "descuento": 0, "total": 0}
    )
    return carrito


@transaction.atomic
def agregar_item(pedido, producto, cantidad, opciones_ids):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden agregar items al carrito.")
    if not producto.disponible:
        raise ValidationError("Producto no disponible.")
    if cantidad <= 0:
        raise ValidationError("Cantidad debe ser mayor a 0.")

    opciones = OpcionProducto.objects.filter(pk__in=opciones_ids, producto=producto)
    tipos_vistos = set()
    recargo_total = Decimal("0")
    for opcion in opciones:
        if opcion.tipo in tipos_vistos:
            raise ValidationError(f"Solo una opcion por tipo: {opcion.tipo}.")
        tipos_vistos.add(opcion.tipo)
        recargo_total += opcion.recargo

    precio_unitario = producto.precio + recargo_total
    item = ItemPedido.objects.create(
        pedido=pedido,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=precio_unitario
    )
    if opciones.exists():
        item.opciones.set(opciones)

    recalcular_totales(pedido)
    return item


@transaction.atomic
def quitar_item(item):
    if item.pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se pueden quitar items del carrito.")
    pedido = item.pedido
    item.delete()
    recalcular_totales(pedido)


def recalcular_totales(pedido):
    subtotal = sum(item.cantidad * item.precio_unitario for item in pedido.items.all())
    descuento = Decimal("0")
    if pedido.codigo_descuento:
        descuento = (subtotal * pedido.codigo_descuento.porcentaje / Decimal("100")).quantize(Decimal("0.01"))
    total = subtotal - descuento
    pedido.subtotal = subtotal
    pedido.descuento = descuento
    pedido.total = total
    pedido.save(update_fields=["subtotal", "descuento", "total"])


@transaction.atomic
def aplicar_codigo(pedido, texto):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede aplicar codigo al carrito.")
    try:
        codigo = CodigoDescuento.objects.get(codigo__iexact=texto.strip().upper())
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("Codigo no existe.")
    if not codigo.activo:
        raise ValidationError("Codigo no esta activo.")
    hoy = timezone.now().date()
    if not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
        raise ValidationError("Codigo fuera de vigencia.")
    if codigo.solo_primer_pedido:
        tiene_pedidos = Pedido.objects.filter(
            cliente=pedido.cliente
        ).exclude(estado__in=[Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO]).exists()
        if tiene_pedidos:
            raise ValidationError("Codigo solo valido para primer pedido.")
    pedido.codigo_descuento = codigo
    pedido.save(update_fields=["codigo_descuento"])
    recalcular_totales(pedido)


@transaction.atomic
def confirmar_pedido(pedido, direccion, metodo_pago):
    if pedido.estado != Pedido.Estado.CARRITO:
        raise ValidationError("Solo se puede confirmar un carrito.")
    if not pedido.items.exists():
        raise ValidationError("El carrito esta vacio.")
    if direccion.usuario != pedido.cliente:
        raise ValidationError("La direccion no pertenece al cliente.")

    pedido.direccion = direccion
    pedido.metodo_pago = metodo_pago
    pedido.save(update_fields=["direccion", "metodo_pago"])

    from apps.pagos.models import Pago
    Pago.objects.create(
        pedido=pedido,
        metodo=metodo_pago,
        monto=pedido.total,
        estado=Pago.Estado.PENDIENTE
    )

    if metodo_pago == Pedido.MetodoPago.EFECTIVO:
        registrar_estado(pedido, Pedido.Estado.RECIBIDO)
    else:
        registrar_estado(pedido, Pedido.Estado.PENDIENTE_PAGO)


def registrar_estado(pedido, nuevo_estado, usuario=None):
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError(f"Transicion no permitida: {pedido.estado} -> {nuevo_estado}")
    pedido.estado = nuevo_estado
    pedido.save(update_fields=["estado"])
    HistorialEstado.objects.create(pedido=pedido, estado=nuevo_estado, usuario=usuario)


@transaction.atomic
def avanzar_pedido(pedido, nuevo_estado, usuario):
    if nuevo_estado not in TRANSICIONES.get(pedido.estado, []):
        raise ValidationError(f"Transicion no permitida: {pedido.estado} -> {nuevo_estado}")

    if nuevo_estado in [Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO_DESPACHO]:
        if not usuario.has_perm("pedidos.preparar_pedido"):
            raise ValidationError("No tiene permiso para preparar pedidos.")
    elif nuevo_estado == Pedido.Estado.EN_CAMINO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar pedidos.")
        from apps.entregas.models import Entrega
        Entrega.objects.create(pedido=pedido, repartidor=usuario, inicio=timezone.now())
    elif nuevo_estado == Pedido.Estado.ENTREGADO:
        if not usuario.has_perm("pedidos.despachar_pedido"):
            raise ValidationError("No tiene permiso para despachar pedidos.")
        try:
            entrega = pedido.entrega
        except Entrega.DoesNotExist:
            raise ValidationError("No hay entrega asociada.")
        if entrega.repartidor != usuario:
            raise ValidationError("Solo el repartidor asignado puede marcar como entregado.")
        entrega.fin = timezone.now()
        entrega.save(update_fields=["fin"])

    registrar_estado(pedido, nuevo_estado, usuario)


def ventas_periodo(dias):
    desde = timezone.now() - timezone.timedelta(days=dias)
    return Pedido.objects.filter(
        estado__in=[Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION,
                    Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO],
        creado__gte=desde
    ).aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("total"))["total"] or Decimal("0")


def productos_mas_pedidos(limite=5):
    from django.db.models import Sum, Count
    return Producto.objects.filter(
        items__pedido__estado__in=[Pedido.Estado.RECIBIDO, Pedido.Estado.EN_PREPARACION,
                                   Pedido.Estado.LISTO_DESPACHO, Pedido.Estado.EN_CAMINO, Pedido.Estado.ENTREGADO]
    ).annotate(total_unidades=Sum("items__cantidad")).order_by("-total_unidades")[:limite]


def ranking_repartidores():
    from django.db.models import Count
    from apps.entregas.models import Entrega
    from collections import defaultdict

    entregas = Entrega.objects.filter(fin__isnull=False).select_related("repartidor")

    # Agrupar por repartidor en Python (minutos es @property, no campo DB)
    datos = defaultdict(lambda: {"entregas": 0, "minutos_totales": 0})
    for e in entregas:
        key = (e.repartidor_id, e.repartidor.username, e.repartidor.first_name, e.repartidor.last_name)
        datos[key]["entregas"] += 1
        if e.minutos is not None:
            datos[key]["minutos_totales"] += e.minutos

    resultado = []
    for (repartidor_id, username, first_name, last_name), d in datos.items():
        minutos_promedio = round(d["minutos_totales"] / d["entregas"], 1) if d["entregas"] > 0 else None
        resultado.append({
            "repartidor__username": username,
            "repartidor__first_name": first_name,
            "repartidor__last_name": last_name,
            "entregas": d["entregas"],
            "minutos_promedio": minutos_promedio,
        })

    resultado.sort(key=lambda x: x["entregas"], reverse=True)
    return resultado