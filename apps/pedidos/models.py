from django.db import models
from django.contrib.auth.models import User


class EstadoPedido(models.TextChoices):
    CARRITO = "carrito", "Carrito"
    PENDIENTE_PAGO = "pendiente_pago", "Pendiente pago"
    RECIBIDO = "recibido", "Recibido"
    EN_PREPARACION = "en_preparacion", "En preparación"
    LISTO_DESPACHO = "listo_despacho", "Listo para despacho"
    EN_CAMINO = "en_camino", "En camino"
    ENTREGADO = "entregado", "Entregado"


class Pedido(models.Model):
    cliente = models.ForeignKey(
        User, related_name="pedidos", on_delete=models.PROTECT
    )
    estado = models.CharField(
        "estado", max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.CARRITO
    )
    direccion = models.ForeignKey(
        "cuentas.Direccion",
        related_name="pedidos",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metodo_pago = models.CharField(
        "metodo de pago", max_length=10, null=True, blank=True
    )
    codigo_descuento = models.ForeignKey(
        "promociones.CodigoDescuento",
        related_name="pedidos",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    subtotal = models.DecimalField("subtotal", max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField("descuento", max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField("total", max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        permissions = [
            ("preparar_pedido", "Puede preparar pedidos"),
            ("despachar_pedido", "Puede despachar pedidos"),
            ("ver_reportes", "Puede ver reportes"),
        ]

    def __str__(self):
        return f"Pedido {self.pk} - {self.cliente.username} ({self.get_estado_display})"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        "Pedido", related_name="items", on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        "catalogo.Producto", related_name="items", on_delete=models.PROTECT
    )
    cantidad = models.PositiveIntegerField("cantidad", default=1)
    precio_unitario = models.DecimalField(
        "precio unitario", max_digits=10, decimal_places=2
    )
    opciones = models.ManyToManyField(
        "catalogo.OpcionProducto", related_name="items", blank=True
    )

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad} en pedido {self.pedido.pk}"


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        "Pedido", related_name="historial", on_delete=models.CASCADE
    )
    estado = models.CharField(
        "estado", max_length=20, choices=EstadoPedido.choices
    )
    fecha = models.DateTimeField("fecha", auto_now_add=True)
    usuario = models.ForeignKey(
        User, related_name="cambios_estado", null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.pedido.pk}: {self.get_estado_display} - {self.fecha}"