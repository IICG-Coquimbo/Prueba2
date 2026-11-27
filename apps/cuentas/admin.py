from django.contrib import admin

from .models import Direccion, PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")
    search_fields = ("usuario__username", "telefono")


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("alias", "direccion", "usuario")
    list_filter = ("alias",)
    search_fields = ("alias", "direccion", "usuario__username")
