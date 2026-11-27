from django.db import models


METODO_EFECTIVO = "efectivo"
METODO_TARJETA = "tarjeta"

METODOS_PAGO = [
    (METODO_EFECTIVO, "Efectivo"),
    (METODO_TARJETA, "Tarjeta"),
]

ESTADO_PENDIENTE = "pendiente"
ESTADO_EXITOSO = "exitoso"
ESTADO_FALLIDO = "fallido"

ESTADOS_PAGO = [
    (ESTADO_PENDIENTE, "Pendiente"),
    (ESTADO_EXITOSO, "Exitoso"),
    (ESTADO_FALLIDO, "Fallido"),
]


class Pago(models.Model):
    pedido = models.OneToOneField(
        "pedidos.Pedido", related_name="pago", on_delete=models.CASCADE
    )
    metodo = models.CharField(max_length=10, choices=METODOS_PAGO)
    estado = models.CharField(max_length=10, choices=ESTADOS_PAGO,
                              default=ESTADO_PENDIENTE)
    referencia = models.CharField(max_length=36, unique=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pago {self.referencia} - {self.estado}"
