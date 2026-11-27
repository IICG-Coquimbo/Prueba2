from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CodigoDescuento(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    porcentaje = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField()
    solo_primer_pedido = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.codigo
