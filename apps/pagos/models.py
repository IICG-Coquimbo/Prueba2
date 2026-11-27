from django.db import models


class Pago(models.Model):
    METODO_CHOICES = [("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")]
    ESTADO_CHOICES = [("pendiente", "Pendiente"), ("exitoso", "Exitoso"), ("fallido", "Fallido")]

    pedido = models.OneToOneField("pedidos.Pedido", related_name="pago", on_delete=models.CASCADE)
    metodo = models.CharField("metodo", max_length=10, choices=METODO_CHOICES)
    estado = models.CharField("estado", max_length=10, choices=ESTADO_CHOICES, default="pendiente")
    referencia = models.CharField("referencia", max_length=36, unique=True)
    monto = models.DecimalField("monto", max_digits=10, decimal_places=2)
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    def __str__(self):
        return f"Pago {self.pedido.pk} - {self.get_estado_display()}"