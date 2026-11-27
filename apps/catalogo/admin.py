from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "disponible")


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ("producto", "tipo", "nombre", "recargo")
