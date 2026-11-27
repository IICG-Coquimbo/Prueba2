from django.contrib.auth.models import User
from django.db import models


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(
        User, related_name="perfil", on_delete=models.CASCADE
    )
    telefono = models.CharField(max_length=20)

    class Meta:
        verbose_name = "PerfilCliente"
        verbose_name_plural = "PerfilClientes"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Direccion(models.Model):
    usuario = models.ForeignKey(
        User, related_name="direcciones", on_delete=models.CASCADE
    )
    alias = models.CharField(max_length=40)
    direccion = models.CharField(max_length=200)
    referencia = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Direccion"
        verbose_name_plural = "Direcciones"

    def __str__(self):
        return f"{self.alias}: {self.direccion}"