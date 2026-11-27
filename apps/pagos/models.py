from django.db import models
from django.contrib.auth.models import User


class MetodoPago(models.TextChoices):
    EFECTIVO = "ef", "Efectivo"
    TARJETA = "tc", "Tarjeta"


class EstadoPago(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EXITOSO = "exitoso", "Exitoso"
    FALLIDO = "fallido", "Fallido"


class Pago(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField(
        "metodo", max_length=10, choices=MetodoPago.choices
    )
    estado = models.CharField(
        "estado", max_length=10, choices=EstadoPago.choices, default="pendiente"
    )
    referencia = models.CharField("referencia", max_length=36, unique=True)
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "pago"
        verbose_name_plural = "pagos"

    def __str__(self):
        return f"Pago {self.pk} - {self.get_estado_display()}"