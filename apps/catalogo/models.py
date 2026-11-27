from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria, related_name="productos", on_delete=models.PROTECT
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen_url = models.URLField(blank=True, null=True)
    disponible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.nombre


class OpcionProducto(models.Model):
    producto = models.ForeignKey(
        Producto, related_name="opciones", on_delete=models.CASCADE
    )
    tipo = models.CharField(max_length=10)
    nombre = models.CharField(max_length=60)
    recargo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "OpcionProducto"
        verbose_name_plural = "OpcionesProducto"

    def __str__(self):
        return self.nombre