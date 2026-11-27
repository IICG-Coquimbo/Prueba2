from django.contrib.auth.models import User
from django.db import models


class Entrega(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido",
        related_name="entrega",
        on_delete=models.CASCADE,
    )
    repartidor = models.ForeignKey(
        User,
        related_name="entregas",
        on_delete=models.PROTECT,
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)

    @property
    def minutos(self):
        if self.fin is None:
            return None
        return int((self.fin - self.inicio).total_seconds() // 60)

    def __str__(self):
        return f"Entrega de {self.pedido}"
