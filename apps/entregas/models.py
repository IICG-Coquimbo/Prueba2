from django.contrib.auth.models import User
from django.db import models


class Entrega(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="entrega", on_delete=models.CASCADE
    )
    repartidor = models.ForeignKey(
        User, related_name="entregas", on_delete=models.PROTECT
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Entregas"

    @property
    def minutos(self):
        if not self.fin:
            return None
        return int((self.fin - self.inicio).total_seconds() // 60)

    def __str__(self):
        return f"Entrega Pedido #{self.pedido_id} - {self.repartidor}"
