from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    pass


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    pass


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    pass
