from django.contrib import admin

from .models import Direccion, PerfilCliente


admin.site.register(PerfilCliente)
admin.site.register(Direccion)
