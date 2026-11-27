from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalogo.models import OpcionProducto, Producto
from apps.cuentas.models import Direccion
from apps.promociones.models import CodigoDescuento


class Pedido(models.Model):
    class Estado(models.TextChoices):
        CARRITO = 'carrito', _('Carrito')
        PENDIENTE_PAGO = 'pendiente_pago', _('Pendiente de pago')
        RECIBIDO = 'recibido', _('Recibido')
        EN_PREPARACION = 'en_preparacion', _('En preparacion')
        LISTO_DESPACHO = 'listo_despacho', _('Listo despacho')
        EN_CAMINO = 'en_camino', _('En camino')
        ENTREGADO = 'entregado', _('Entregado')

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', _('Efectivo')
        TARJETA = 'tarjeta', _('Tarjeta')

    cliente = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pedidos',
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.CARRITO,
    )
    direccion = models.ForeignKey(
        Direccion,
        on_delete=models.SET_NULL,
        related_name='pedidos',
        null=True,
        blank=True,
    )
    metodo_pago = models.CharField(
        max_length=10,
        choices=MetodoPago.choices,
        blank=True,
    )
    codigo_descuento = models.ForeignKey(
        CodigoDescuento,
        on_delete=models.SET_NULL,
        related_name='pedidos',
        null=True,
        blank=True,
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('preparar_pedido', 'Puede preparar pedidos'),
            ('despachar_pedido', 'Puede despachar pedidos'),
            ('ver_reportes', 'Puede ver reportes'),
        ]

    def __str__(self):
        return f'Pedido #{self.pk} de {self.cliente.username}'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='items',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='items',
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    opciones = models.ManyToManyField(
        OpcionProducto,
        related_name='items',
        blank=True,
    )

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'


class HistorialEstado(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historial',
    )
    estado = models.CharField(max_length=20, choices=Pedido.Estado.choices)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='cambios_estado',
        null=True,
    )

    def __str__(self):
        return f'Pedido #{self.pedido_id} - {self.get_estado_display()}'
