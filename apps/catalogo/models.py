from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria, related_name="productos", on_delete=models.PROTECT
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
        TAMANO = "tamano", "Tamano"
        LECHE = "leche", "Leche"
        AZUCAR = "azucar", "Azucar"

    producto = models.ForeignKey(
        Producto, related_name="opciones", on_delete=models.CASCADE
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    nombre = models.CharField(max_length=60)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"
