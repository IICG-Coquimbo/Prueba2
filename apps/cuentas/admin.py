from django.contrib import admin
from .models import PerfilCliente, Direccion


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")
    search_fields = ("usuario__username", "telefono")


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "alias", "direccion")
    search_fields = ("usuario__username", "alias", "direccion")