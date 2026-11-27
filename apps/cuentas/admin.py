from django.contrib import admin

from .models import Direccion, PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefono")
    search_fields = ("usuario__username", "usuario__email", "telefono")
    list_select_related = ("usuario",)


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ("alias", "usuario", "direccion")
    list_filter = ("usuario",)
    search_fields = ("alias", "direccion", "referencia", "usuario__username")
    list_select_related = ("usuario",)
