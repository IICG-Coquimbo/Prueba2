from django.core.validators import RegexValidator
from django.db import models

from apps.pedidos.models import Pedido


class Pago(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EXITOSO = "exitoso", "Exitoso"
        FALLIDO = "fallido", "Fallido"

    pedido = models.OneToOneField(
        Pedido, related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField(max_length=10, choices=Pedido.MetodoPago.choices)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    referencia = models.CharField(
        max_length=36,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"\A[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z",
                message="La referencia debe ser un UUID en formato de texto con guiones.",
            )
        ],
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.referencia} (pedido #{self.pedido_id})"
