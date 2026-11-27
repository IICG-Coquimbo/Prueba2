from django.contrib.auth.models import User
from django.db import models


class EstadoPedido(models.TextChoices):
    CARRITO = "carrito", "Carrito"
    PENDIENTE_PAGO = "pendiente_pago", "Pendiente de pago"
    RECIBIDO = "recibido", "Recibido"
    EN_PREPARACION = "en_preparacion", "En preparación"
    LISTO_DESPACHO = "listo_despacho", "Listo despacho"
    EN_CAMINO = "en_camino", "En camino"
    ENTREGADO = "entregado", "Entregado"


class Pedido(models.Model):
    cliente = models.ForeignKey(
        User,
        related_name="pedidos",
        on_delete=models.PROTECT,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.CARRITO,
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
            ("preparar_pedido", "Puede preparar pedidos"),
            ("despachar_pedido", "Puede despachar pedidos"),
            ("ver_reportes", "Puede ver reportes"),
        ]

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.username}"


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
        return f"{self.cantidad} x {self.producto.nombre}"


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name="historial",
        on_delete=models.CASCADE,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
    )
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User,
        related_name="cambios_estado",
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return f"{self.pedido.id} -> {self.estado}"
