from django.contrib import admin

from .models import Categoria, OpcionProducto, Producto


class OpcionProductoInline(admin.TabularInline):
    model = OpcionProducto
    extra = 1


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "categoria", "precio", "disponible"]
    list_filter = ["categoria", "disponible"]
    search_fields = ["nombre", "descripcion"]
    inlines = [OpcionProductoInline]


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ["producto", "tipo", "nombre", "recargo"]
    list_filter = ["tipo", "producto"]
    search_fields = ["nombre", "producto__nombre"]
