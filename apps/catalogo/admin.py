from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "disponible")
    list_filter = ("categoria", "disponible")
    search_fields = ("nombre",)
    list_select_related = ("categoria",)


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "producto", "tipo", "recargo")
    list_filter = ("tipo",)
    search_fields = ("nombre", "producto__nombre")
    list_select_related = ("producto",)
