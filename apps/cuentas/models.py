from django.db import models
from django.contrib.auth.models import User


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(
        User, related_name="perfil", on_delete=models.CASCADE
    )
    telefono = models.CharField("telefono", max_length=20)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Direccion(models.Model):
    usuario = models.ForeignKey(
        User, related_name="direcciones", on_delete=models.CASCADE
    )
    alias = models.CharField("alias", max_length=40)
    direccion = models.CharField("direccion", max_length=200)
    referencia = models.CharField("referencia", max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "direccion"
        verbose_name_plural = "direcciones"

    def __str__(self):
        return f"{self.alias} - {self.usuario.username}"