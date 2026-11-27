from django.contrib import admin

from apps.catalogo.models import Categoria, OpcionProducto, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


class OpcionProductoInline(admin.TabularInline):
    model = OpcionProducto
    extra = 0


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "disponible")
    list_filter = ("disponible", "categoria")
    search_fields = ("nombre",)
    inlines = [OpcionProductoInline]


@admin.register(OpcionProducto)
class OpcionProductoAdmin(admin.ModelAdmin):
    list_display = ("producto", "tipo", "nombre", "recargo")
    list_filter = ("tipo",)
    search_fields = ("nombre", "producto__nombre")
