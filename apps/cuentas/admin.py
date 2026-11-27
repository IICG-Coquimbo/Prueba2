from django.contrib import admin
from .models import PerfilCliente, Direccion


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")
    search_fields = ("usuario__username", "usuario__email", "telefono")


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("alias", "usuario", "direccion")
    search_fields = ("alias", "direccion", "usuario__username")
    list_filter = ("usuario",)