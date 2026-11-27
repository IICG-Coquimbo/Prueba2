from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class CodigoDescuento(models.Model):
    codigo = models.CharField("codigo", max_length=20, unique=True)
    porcentaje = models.PositiveIntegerField(
        "porcentaje", validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField("vigente hasta")
    solo_primer_pedido = models.BooleanField("solo primer pedido", default=False)
    activo = models.BooleanField("activo", default=True)

    def __str__(self):
        return f"{self.codigo} - {self.porcentaje}%"