from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

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
    TIPO_CHOICES = [
        ("tamano", "Tamaño"),
        ("leche", "Leche"),
        ("azucar", "Azúcar"),
    ]

    producto = models.ForeignKey(
        Producto, related_name="opciones", on_delete=models.CASCADE
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    nombre = models.CharField(max_length=60)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre}"
