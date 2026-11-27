from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    nombre = models.CharField("nombre", max_length=80, unique=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria, related_name="productos", on_delete=models.PROTECT
    )
    nombre = models.CharField("nombre", max_length=120)
    descripcion = models.TextField("descripcion", null=True, blank=True)
    precio = models.DecimalField("precio", max_digits=10, decimal_places=2)
    imagen_url = models.URLField("imagen_url", null=True, blank=True)
    disponible = models.BooleanField("disponible", default=True)

    def __str__(self):
        return self.nombre


class OpcionProducto(models.Model):
    class TipoOpcion(models.TextChoices):
        TAMANO = "tm", "Tamaño"
        LECHE = "lc", "Leche"
        AZUCAR = "az", "Azúcar"

    producto = models.ForeignKey(
        Producto, related_name="opciones", on_delete=models.CASCADE
    )
    tipo = models.CharField("tipo", max_length=10, choices=TipoOpcion.choices)
    nombre = models.CharField("nombre", max_length=60)
    recargo = models.DecimalField(
        "recargo", max_digits=10, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = "opción de producto"
        verbose_name_plural = "opciones de producto"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"