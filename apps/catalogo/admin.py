from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "disponible")
    search_fields = ("nombre", "descripcion")
    list_filter = ("categoria", "disponible")


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "producto", "tipo", "recargo")
    search_fields = ("nombre", "producto__nombre")
    list_filter = ("tipo",)
