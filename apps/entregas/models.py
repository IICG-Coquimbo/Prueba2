from django.db import models
from django.contrib.auth.models import User


class Entrega(models.Model):
    pedido = models.OneToOneField("pedidos.Pedido", related_name="entrega", on_delete=models.CASCADE)
    repartidor = models.ForeignKey(User, related_name="entregas", on_delete=models.PROTECT)
    inicio = models.DateTimeField("inicio")
    fin = models.DateTimeField("fin", null=True, blank=True)

    def __str__(self):
        return f"Entrega {self.pedido.pk} - {self.inicio}"

    @property
    def minutos(self):
        if self.fin:
            return (self.fin - self.inicio).total_seconds() / 60
        return None