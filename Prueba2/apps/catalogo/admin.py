from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(OpcionProducto)
