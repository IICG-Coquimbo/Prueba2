from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ("fecha",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "total", "creado")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("cliente__username",)
    date_hierarchy = "creado"
    inlines = (ItemPedidoInline, HistorialEstadoInline)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("producto",)
    search_fields = ("pedido__id", "producto__nombre")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado",)
    search_fields = ("pedido__id",)
