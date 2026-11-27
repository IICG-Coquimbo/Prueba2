from django.conf import settings
from django.db import models


class Pedido(models.Model):
    ESTADO_CHOICES = models.TextChoices(
        "Estado",
        "carrito pendiente_pago recibido en_preparacion listo_despacho en_camino entregado",
    )

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="pedidos", on_delete=models.PROTECT
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES.choices,
        default=ESTADO_CHOICES.carrito,
    )
    direccion = models.ForeignKey(
        "cuentas.Direccion",
        related_name="pedidos",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    metodo_pago = models.CharField(
        max_length=10,
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        blank=True,
    )
    codigo_descuento = models.ForeignKey(
        "promociones.CodigoDescuento",
        related_name="pedidos",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        permissions = [
            ("preparar_pedido", "Puede preparar pedido"),
            ("despachar_pedido", "Puede despachar pedido"),
            ("ver_reportes", "Puede ver reportes"),
        ]

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.username}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, related_name="items", on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        "catalogo.Producto", related_name="items", on_delete=models.PROTECT
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    opciones = models.ManyToManyField(
        "catalogo.OpcionProducto", related_name="items", blank=True
    )

    class Meta:
        verbose_name = "ItemPedido"
        verbose_name_plural = "ItemsPedido"

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad} en Pedido {self.pedido.id}"


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        Pedido, related_name="historial", on_delete=models.CASCADE
    )
    estado = models.CharField(max_length=20)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="cambios_estado",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "HistorialEstado"
        verbose_name_plural = "HistorialEstados"

    def __str__(self):
        return f"Pedido {self.pedido.id}: {self.estado} - {self.fecha}"