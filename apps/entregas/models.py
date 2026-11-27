from django.db import models
from django.contrib.auth.models import User


class Entrega(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="entrega", on_delete=models.CASCADE
    )
    repartidor = models.ForeignKey(
        User, related_name="entregas", on_delete=models.PROTECT
    )
    inicio = models.DateTimeField("cuando pasa a en_camino")
    fin = models.DateTimeField("cuando pasa a entregado", null=True, blank=True)

    @property
    def minutos(self):
        if self.fin and self.inicio:
            delta = self.fin - self.inicio
            return delta.total_seconds() / 60
        return None

    def __str__(self):
        return f"Entrega {self.pedido.pk} - Repartidor: {self.repartidor.username}"