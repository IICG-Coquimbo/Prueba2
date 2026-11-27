from django.contrib import admin
from .models import Categoria, Producto, OpcionProducto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "disponible")
    list_filter = ("categoria", "disponible")
    search_fields = ("nombre", "descripcion")


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "producto", "tipo", "recargo")
    list_filter = ("tipo", "producto")
    search_fields = ("nombre", "producto__nombre")