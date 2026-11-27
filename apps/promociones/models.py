from django.db import models


class CodigoDescuento(models.Model):
    codigo = models.CharField("codigo", max_length=20, unique=True)
    porcentaje = models.PositiveIntegerField("porcentaje")
    vigente_desde = models.DateField("vigente desde")
    vigente_hasta = models.DateField("vigente hasta")
    solo_primer_pedido = models.BooleanField("solo primer pedido", default=False)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "código de descuento"
        verbose_name_plural = "códigos de descuento"

    def __str__(self):
        return self.codigo