from django.conf import settings
from django.db import models


class Entrega(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="entrega", on_delete=models.CASCADE
    )
    repartidor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="entregas",
        on_delete=models.PROTECT,
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"

    @property
    def minutos(self):
        if self.fin:
            return (self.fin - self.inicio).total_seconds() / 60
        return None

    def __str__(self):
        return f"Entrega Pedido {self.pedido.id} - Repartidor: {self.repartidor.username}"