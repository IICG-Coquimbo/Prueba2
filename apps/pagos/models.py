from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.pedidos.models import Pedido


class Pago(models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = 'efectivo', _('Efectivo')
        TARJETA = 'tarjeta', _('Tarjeta')

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', _('Pendiente')
        EXITOSO = 'exitoso', _('Exitoso')
        FALLIDO = 'fallido', _('Fallido')

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name='pago',
    )
    metodo = models.CharField(max_length=10, choices=Metodo.choices)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    referencia = models.CharField(max_length=36, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Pago {self.referencia} - {self.get_estado_display()}'
