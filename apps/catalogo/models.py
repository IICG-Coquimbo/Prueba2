from django.db import models
from django.utils.translation import gettext_lazy as _


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen_url = models.URLField(blank=True)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class OpcionProducto(models.Model):
    class Tipo(models.TextChoices):
        TAMANO = 'tamano', _('Tamano')
        LECHE = 'leche', _('Leche')
        AZUCAR = 'azucar', _('Azucar')

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    nombre = models.CharField(max_length=60)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.nombre}'
