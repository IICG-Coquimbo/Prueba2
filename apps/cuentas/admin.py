from django.contrib import admin

from .models import Direccion, PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("alias", "usuario", "direccion")
