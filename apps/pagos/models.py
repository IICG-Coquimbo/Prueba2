from django.db import models


class Pago(models.Model):
    metodo_choices = (
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
    )
    estado_choices = (
        ("pendiente", "Pendiente"),
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
    )

    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField("metodo", max_length=10, choices=metodo_choices)
    estado = models.CharField(
        "estado", max_length=10, choices=estado_choices, default="pendiente"
    )
    referencia = models.CharField("referencia", max_length=36, unique=True)
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    def __str__(self):
        return f"Pago {self.pk} - {self.get_estado_display} - ${self.monto}"