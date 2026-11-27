"""Modelos de la app cuentas segun docs/modelo_datos.md."""

from django.contrib.auth.models import User
from django.db import models


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(
        User,
        related_name="perfil",
        on_delete=models.CASCADE,
    )
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

    class Meta:
        verbose_name = "Perfil de cliente"
        verbose_name_plural = "Perfiles de clientes"


class Direccion(models.Model):
    usuario = models.ForeignKey(
        User,
        related_name="direcciones",
        on_delete=models.CASCADE,
    )
    alias = models.CharField(max_length=40)
    direccion = models.CharField(max_length=200)
    referencia = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.alias} - {self.usuario.username}"

    class Meta:
        verbose_name = "Direccion"
        verbose_name_plural = "Direcciones"
