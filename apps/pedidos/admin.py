from django.contrib import admin
from .models import Pedido, ItemPedido, HistorialEstado


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "cliente", "estado", "metodo_pago",
        "subtotal", "descuento", "total", "creado",
    )
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = ("cliente__username", "id")
    inlines = [ItemPedidoInline]


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("producto",)
    search_fields = ("pedido__id", "producto__nombre")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado", "fecha")
    search_fields = ("pedido__id",)
