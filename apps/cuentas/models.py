from django.contrib.auth.models import User
from django.db import models


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    telefono = models.CharField(max_length=20)

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


class Direccion(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='direcciones',
    )
    alias = models.CharField(max_length=40)
    direccion = models.CharField(max_length=200)
    referencia = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f'{self.alias} - {self.direccion}'
