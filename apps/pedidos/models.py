from django.db import models
from django.contrib.auth.models import User


ESTADO_CARRITO = "carrito"
ESTADO_PENDIENTE_PAGO = "pendiente_pago"
ESTADO_RECIBIDO = "recibido"
ESTADO_EN_PREPARACION = "en_preparacion"
ESTADO_LISTO_DESPACHO = "listo_despacho"
ESTADO_EN_CAMINO = "en_camino"
ESTADO_ENTREGADO = "entregado"

ESTADOS_PEDIDO = [
    (ESTADO_CARRITO, "Carrito"),
    (ESTADO_PENDIENTE_PAGO, "Pendiente de pago"),
    (ESTADO_RECIBIDO, "Recibido"),
    (ESTADO_EN_PREPARACION, "En preparacion"),
    (ESTADO_LISTO_DESPACHO, "Listo despacho"),
    (ESTADO_EN_CAMINO, "En camino"),
    (ESTADO_ENTREGADO, "Entregado"),
]

METODO_EFECTIVO = "efectivo"
METODO_TARJETA = "tarjeta"

METODOS_PAGO = [
    (METODO_EFECTIVO, "Efectivo"),
    (METODO_TARJETA, "Tarjeta"),
]


class Pedido(models.Model):
    cliente = models.ForeignKey(
        User, related_name="pedidos", on_delete=models.PROTECT
    )
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO,
                              default=ESTADO_CARRITO)
    direccion = models.ForeignKey(
        "cuentas.Direccion", related_name="pedidos",
        null=True, blank=True, on_delete=models.SET_NULL
    )
    metodo_pago = models.CharField(max_length=10, choices=METODOS_PAGO,
                                   blank=True)
    codigo_descuento = models.ForeignKey(
        "promociones.CodigoDescuento", related_name="pedidos",
        null=True, blank=True, on_delete=models.SET_NULL
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2,
                                   default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2,
                                    default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2,
                                default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("preparar_pedido", "Puede preparar pedidos"),
            ("despachar_pedido", "Puede despachar pedidos"),
            ("ver_reportes", "Puede ver reportes"),
        ]

    def __str__(self):
        return f"Pedido {self.pk} - {self.cliente.username}"


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

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        Pedido, related_name="historial", on_delete=models.CASCADE
    )
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User, related_name="cambios_estado", null=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.pedido} -> {self.estado}"
