import uuid

from django.db import models

from apps.pedidos.models import MetodoPago, Pedido


class EstadoPago(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EXITOSO = "exitoso", "Exitoso"
    FALLIDO = "fallido", "Fallido"


def generar_referencia():
    return str(uuid.uuid4())


class Pago(models.Model):
    pedido = models.OneToOneField(
        Pedido,
        related_name="pago",
        on_delete=models.CASCADE,
    )
    metodo = models.CharField(max_length=10, choices=MetodoPago.choices)
    estado = models.CharField(
        max_length=10,
        choices=EstadoPago.choices,
        default="pendiente",
    )
    referencia = models.CharField(
        max_length=36,
        unique=True,
        default=generar_referencia,
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.referencia}"
