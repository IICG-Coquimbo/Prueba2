from django.conf import settings
from django.db import models


class Pago(models.Model):
    METODO_CHOICES = models.TextChoices(
        "Metodo", "efectivo tarjeta"
    )
    ESTADO_CHOICES = models.TextChoices(
        "Estado", "pendiente exitoso fallido"
    )

    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField(
        max_length=10,
        choices=METODO_CHOICES.choices,
        default=METODO_CHOICES.efectivo,
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES.choices,
        default=ESTADO_CHOICES.pendiente,
    )
    referencia = models.CharField(max_length=36, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago {self.referencia} - {self.get_estado_display()}"