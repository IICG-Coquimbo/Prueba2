from django.db import models


class MetodoPago(models.TextChoices):
    EFECTIVO = "efectivo", "Efectivo"
    TARJETA = "tarjeta", "Tarjeta"


class EstadoPago(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EXITOSO = "exitoso", "Exitoso"
    FALLIDO = "fallido", "Fallido"


class Pago(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido",
        related_name="pago",
        on_delete=models.CASCADE,
    )
    metodo = models.CharField(max_length=10, choices=MetodoPago.choices)
    estado = models.CharField(
        max_length=10,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    referencia = models.CharField(max_length=36, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.referencia} - {self.estado}"
