from django.db import models


class Pago(models.Model):
    METODO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
    ]

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
    ]

    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField(max_length=10, choices=METODO_CHOICES)
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default="pendiente"
    )
    referencia = models.CharField(max_length=36, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.referencia} - {self.estado}"
