from django.conf import settings
from django.db import models


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="perfil",
        on_delete=models.CASCADE,
    )
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return f"Perfil de {self.usuario}"


class Direccion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="direcciones",
        on_delete=models.CASCADE,
    )
    alias = models.CharField(max_length=40)
    direccion = models.CharField(max_length=200)
    referencia = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.alias}: {self.direccion}"
