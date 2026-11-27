from django.contrib import admin

from .models import Direccion, PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    pass


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    pass
