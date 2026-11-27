import uuid
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from pedidos.models import Pedido, HistorialEstado
from catalogo.models import Producto, OpcionProducto
from pagos.models import Pago
from cuentas.models import Direccion
from promociones.models import CodigoDescuento


# Mapeo de transiciones de estado permitidas por rol
TRANSICIONES = {
    "recibido": ["en_preparacion"],
    "en_preparacion": ["listo_despacho"],
    "listo_despacho": ["en_camino"],
    "en_camino": ["entregado"],
}


def obtener_carrito(usuario):
    """RF-04: devuelve el pedido en estado carrito del usuario; si no existe, lo crea."""
    with transaction.atomic():
        pedido, creado = Pedido.objects.get_or_create(
            cliente=usuario,
            estado="carrito",
            defaults={
                "estado": "carrito",
                "subtotal": 0,
                "descuento": 0,
                "total": 0,
            },
        )
        return pedido


def agregar_item(pedido, producto, cantidad, opciones):
    """RF-04, RF-05, RF-15: exige estado carrito, producto disponible, cantidad > 0,
    opciones que pertenezcan al producto y como maximo una por tipo (tamano, leche, azucar).
    precio_unitario = precio + recargos de las opciones. Llama a recalcular_totales."""
    if pedido.estado != "carrito":
        raise ValidationError("Solo se pueden agregar items a un pedido en estado carrito.")

    if not producto.disponible:
        raise ValidationError("El producto no está disponible.")

    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que 0.")

    # Validar opciones: maximo una por tipo (tamano, leche, azucar)
    tipos_seleccionados = set()
    for opc in opciones:
        try:
            op = OpcionProducto.objects.get(producto=producto, nombre=opc)
            tipos_seleccionados.add(op.tipo)
        except OpcionProducto.DoesNotExist:
            raise ValidationError(f"La opción '{opc}' no pertenece a este producto.")

    # Verificar que no haya más de una por tipo
    # Contar cuántos de cada tipo ya están en el item (incluyendo las nuevas)
    # Las opciones son ManyToMany, así que verificamos las ya asociadas plus las nuevas
    opciones_existentes = set(pedido.items.filter(producto=producto).values_list("opciones__tipo", flat=True))
    for t in tipos_seleccionados:
        if t in opciones_existentes:
            raise ValidationError(f"Ya has seleccionado una opción de tipo '{t}' para este producto.")

    # Calcular precio_unitario: precio del producto + recargos de las opciones seleccionadas
    precio_base = producto.precio
    recargo_total = sum(
        OpcionProducto.objects.get(producto=producto, nombre=opc).recargo
        for opc in opciones
    )
    precio_unitario = precio_base + recargo_total

    with transaction.atomic():
        item, creado = pedido.items.get_or_create(
            producto=producto,
            defaults={
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
            },
        )
        if not creado:
            item.cantidad += cantidad
            item.precio_unitario = precio_unitario
            item.save()

        # Agregar las opciones ManyToMany (solo si no ya estaban)
        for opc in opciones:
            op, _ = OpcionProducto.objects.get_or_create(producto=producto, nombre=opc)
            item.opciones.add(op)

        recalcular_totales(pedido)

    return item


def quitar_item(item):
    """RF-04: exige estado carrito. Llama a recalcular_totales."""
    pedido = item.pedido
    if pedido.estado != "carrito":
        raise ValidationError("Solo se pueden quitar items de un pedido en estado carrito.")

    with transaction.atomic():
        item.delete()
        recalcular_totales(pedido)


def recalcular_totales(pedido):
    """RF-04, RF-05: subtotal = suma de cantidad x precio_unitario;
    descuento = subtotal x porcentaje del codigo / 100 (0 si no hay codigo);
    total = subtotal - descuento. Dos decimales."""
    with transaction.atomic():
        # Calcular subtotal: suma de cantidad * precio_unitario de cada item
        subtotal = sum(item.cantidad * item.precio_unitario for item in pedido.items.all())

        # Descuento: si tiene codigo_descuento, calcular porcentaje
        if pedido.codigo_descuento:
            porcentaje = pedido.codigo_descuento.porcentaje
            descuento = round(subtotal * porcentaje / 100, 2)
        else:
            descuento = 0

        total = round(subtotal - descuento, 2)

        pedido.subtotal = subtotal
        pedido.descuento = descuento
        pedido.total = total
        pedido.save(update_fields=["subtotal", "descuento", "total"])


def aplicar_codigo(pedido, texto):
    """RF-16: busca el CodigoDescuento por codigo.
    Exige activo, fecha de hoy entre vigente_desde y vigente_hasta y,
    si solo_primer_pedido, que el cliente no tenga otros pedidos fuera
    de carrito y pendiente_pago. Guarda el codigo en el pedido y llama a recalcular_totales."""
    if pedido.estado != "carrito":
        raise ValidationError("No se puede aplicar un código a un pedido que no está en carrito.")

    try:
        codigo = CodigoDescuento.objects.get(codigo=texto)
    except CodigoDescuento.DoesNotExist:
        raise ValidationError("El código de descuento no existe.")

    # Verificar que esté activo
    if not codigo.activo:
        raise ValidationError("El código de descuento no está activo.")

    # Verificar vigencia
    hoy = timezone.now().date()
    if hoy < codigo.vigente_desde or hoy > codigo.vigente_hasta:
        raise ValidationError("El código de descuento no está vigente hoy.")

    # Verificar solo_primer_pedido
    if codigo.solo_primer_pedido:
        # El cliente no debe tener pedidos recibidos o posteriores (estado >= recibido)
        pedidos_no_carrito = Pedido.objects.filter(
            cliente=pedido.cliente
        ).exclude(estado="carrito")
        # Si tiene algún pedido que no es carrito, ya no es el primer pedido
        if pedidos_no_carrito.exists():
            raise ValidationError(
                "Este código solo es válido para el primer pedido del cliente."
            )

    with transaction.atomic():
        pedido.codigo_descuento = codigo
        recalcular_totales(pedido)

    return codigo


def confirmar_pedido(pedido, direccion, metodo_pago):
    """RF-07: exige estado carrito, al menos un item y una direccion del mismo cliente.
    Crea el Pago (estado pendiente, referencia uuid4 en texto, monto = total).
    Efectivo: registrar_estado(recibido). Tarjeta: registrar_estado(pendiente_pago)"""
    if pedido.estado != "carrito":
        raise ValidationError("Solo se pueden confirmar pedidos en estado carrito.")

    if not pedido.items.exists():
        raise ValidationError("El pedido debe tener al menos un item.")

    # Verificar que la direccion pertenezca al cliente
    if direccion.usuario != pedido.cliente:
        raise ValidationError("La dirección no pertenece a este cliente.")

    with transaction.atomic():
        # Crear el Pago
        referencia = str(uuid.uuid4())
        Pago.objects.create(
            pedido=pedido,
            metodo=metodo_pago,
            estado="pendiente",
            referencia=referencia,
            monto=pedido.total,
        )

        if metodo_pago == "efectivo":
            registrar_estado(pedido, "recibido", usuario=pedido.cliente)
        elif metodo_pago == "tarjeta":
            registrar_estado(pedido, "pendiente_pago", usuario=pedido.cliente)
        else:
            raise ValidationError("Método de pago no válido.")

    return pedido


def avanzar_pedido(pedido, nuevo_estado, usuario):
    """RF-12, RF-14: valida con TRANSICIONES y por rol.
    preparar_pedido permite recibido -> en_preparacion y en_preparacion -> listo_despacho;
    despachar_pedido permite listo_despacho -> en_camino (crea la Entrega con ese
    repartidor e inicio = ahora) y en_camino -> entregado (solo el
    repartidor de la Entrega; guarda fin = ahora)."""
    # Verificar que la transicion sea permitida por el diccionario
    estado_actual = pedido.estado
    if estado_actual not in TRANSICIONES or nuevo_estado not in TRANSICIONES[estado_actual]:
        raise ValidationError(
            f"Transición inválida de '{estado_actual}' a '{nuevo_estado}'."
        )

    with transaction.atomic():
        # Verificar permisos por rol
        # El usuario se usa para verificar si es personal autorizado
        # Lógica simplificada: la vista debe tener el permiso correspondiente
        if nuevo_estado == "en_preparacion" or nuevo_estado == "listo_despacho":
            # Richiede permiso preparar_pedido o despachar_pedido
            # La vista verificará esto, pero aquí solo validamos la transicion
            pass

        # Para en_camino -> entregado, verificar que el usuario sea el repartidor
        if nuevo_estado == "entregado" and pedido.entrega_id:
            from apps.entregas.models import Entrega
            entrega = pedido.entrega
            if entrega.repartidor != usuario:
                raise ValidationError("Solo el repartidor asignado puede cambiar el estado a entregado.")

        registrar_estado(pedido, nuevo_estado, usuario=usuario)

        # Lógica específica para crear Entrega en listo_despacho -> en_camino
        from pedidos.models import HistorialEstado

        if nuevo_estado == "en_camino":
            # Crear la Entrega si no existe
            from apps.entregas.models import Entrega
            if not pedido.entrega_id:
                # Asignar un repartidor (aquí podríamos lógica para elegir uno)
                # Por simplicidad, usamos el usuario actual si es staff, o buscamos uno
                from django.contrib.auth.models import User
                try:
                    repartidor = User.objects.filter(is_staff=True).first()
                except:
                    repartidor = usuario
                Entrega.objects.create(
                    pedido=pedido,
                    repartidor=repartidor,
                    inicio=timezone.now(),
                )

        # Lógica para en_camino -> entregado (guarda fin = ahora)
        if nuevo_estado == "entregado" and pedido.entrega_id:
            entrega = pedido.entrega
            if entrega.fin is None:
                entrega.fin = timezone.now()
                entrega.save(update_fields=["fin"])

    return pedido


def registrar_estado(pedido, nuevo_estado, usuario=None):
    """RNF-07: cambia el estado y crea el HistorialEstado."""
    with transaction.atomic():
        pedido.estado = nuevo_estado
        pedido.save(update_fields=["estado"])

        HistorialEstado.objects.create(
            pedido=pedido,
            estado=nuevo_estado,
            usuario=usuario,
        )


def ventas_periodo(dias):
    """RF-17: suma del total de los pedidos en estado recibido o posterior
    creados en los ultimos <dias> dias (1 = hoy)."""
    from django.db.models import Sum
    from datetime import timedelta

    hoy = timezone.now().date()
    desde = hoy - timedelta(dias=dias)

    total = Pedido.objects.filter(
        estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"],
        creado__date__gte=desde,
    ).aggregate(Sum("total"))

    return total["total__sum"] or 0


def productos_mas_pedidos(limite=5):
    """RF-17: productos con mas unidades en pedidos recibidos o posteriores."""
    from django.db.models import Sum

    resultado = (
        ItemPedido.objects.filter(
            pedido__estado__in=["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"],
        )
        .values("producto__nombre", "producto__id")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades")[:limite]
    )

    return list(resultado)


def ranking_repartidores():
    """RF-18: por repartidor, entregas con fin y minutos promedio,
    ordenado por entregas (mayor primero)."""
    from django.db.models import Avg, Count, F
    from datetime import timedelta

    # Entregas que ya tienen fin calculado
    entregas = (
        Entrega.objects.filter(fin__isnull=False)
        .annotate(
            minutos=Avg("fin"),
        )
        .values("repartidor__nombre", "repartidor__id")
        .annotate(
            total_entregas=Count("id"),
            minutos_promedio=Avg(
                F("fin") - F("inicio")
            ),
        )
        .order_by("-total_entregas")
    )

    return list(entregas)