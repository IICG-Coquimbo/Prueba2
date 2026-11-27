from django.db import models


class CodigoDescuento(models.Model):
    codigo = models.CharField("codigo", max_length=20, unique=True)
    porcentaje = models.PositiveIntegerField("porcentaje")
    vigente_desde = models.DateField("vigente_desde")
    vigente_hasta = models.DateField("vigente_hasta")
    solo_primer_pedido = models.BooleanField("solo_primer_pedido", default=False)
    activo = models.BooleanField("activo", default=True)

    def __str__(self):
        return self.codigo