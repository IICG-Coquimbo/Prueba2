from django.contrib.auth.models import User
from django.db import models


class Entrega(models.Model):
    pedido = models.OneToOneField("pedidos.Pedido", related_name="entrega", on_delete=models.CASCADE)
    repartidor = models.ForeignKey(User, related_name="entregas", on_delete=models.PROTECT)
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)

    @property
    def minutos(self):
        if self.inicio and self.fin:
            delta = self.fin - self.inicio
            return int(delta.total_seconds() // 60)
        return None

    def __str__(self):
        return f"Entrega - Pedido #{self.pedido.pk}"
