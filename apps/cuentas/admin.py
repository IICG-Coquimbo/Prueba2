from django.contrib import admin
from django.contrib.auth.models import User

from .models import Direccion, PerfilCliente


admin.site.register(PerfilCliente)
admin.site.register(Direccion)
