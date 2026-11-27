from django.contrib import admin

from .models import Direccion, PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name", "telefono")


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("alias", "usuario", "direccion", "referencia")
    search_fields = ("alias", "direccion", "referencia", "usuario__username")
    list_filter = ("usuario",)
