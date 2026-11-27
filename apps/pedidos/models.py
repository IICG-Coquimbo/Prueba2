from django.contrib.auth.models import User
from django.db import models


class Pedido(models.Model):
    class Estado(models.TextChoices):
        CARTRITO = "carrito", "carrito"
        PENDIENTE_PAGO = "pendiente_pago", "pendiente_pago"
        RECIBIDO = "recibido", "recibido"
        EN_PREPARACION = "en_preparacion", "en_preparacion"
        LISTO_DESPACHO = "listo_despacho", "listo_despacho"
        EN_CAMINO = "en_camino", "en_camino"
        ENTREGADO = "entregado", "entregado"

    class MetodoPago(models.TextChoices):
        EFECTIVO = "efectivo", "efectivo"
        TARJETA = "tarjeta", "tarjeta"

    cliente = models.ForeignKey(
        User,
        related_name="pedidos",
        on_delete=models.PROTECT,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.CARTRITO,
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
        choices=MetodoPago.choices,
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
        permissions = [
            ("preparar_pedido", "Preparar pedido"),
            ("despachar_pedido", "Despachar pedido"),
            ("ver_reportes", "Ver reportes"),
        ]

    def __str__(self):
        return f"Pedido {self.pk}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name="items",
        on_delete=models.CASCADE,
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        related_name="items",
        on_delete=models.PROTECT,
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    opciones = models.ManyToManyField(
        "catalogo.OpcionProducto",
        related_name="items",
        blank=True,
    )

    def __str__(self):
        return f"{self.cantidad} x {self.producto}"


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name="historial",
        on_delete=models.CASCADE,
    )
    estado = models.CharField(max_length=20, choices=Pedido.Estado.choices)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User,
        related_name="cambios_estado",
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return f"{self.pedido} - {self.estado}"
