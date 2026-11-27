from django.contrib.auth.models import User
from django.db import models

from apps.pedidos.models import Pedido


class Entrega(models.Model):
    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name='entrega',
    )
    repartidor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='entregas',
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)

    @property
    def minutos(self):
        if self.fin is None:
            return None
        return int((self.fin - self.inicio).total_seconds() // 60)

    def __str__(self):
        return f'Entrega del pedido #{self.pedido_id}'
