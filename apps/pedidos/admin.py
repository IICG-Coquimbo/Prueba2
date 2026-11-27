from django.contrib import admin
from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ["producto", "cantidad", "precio_unitario", "opciones"]


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ["id", "cliente", "estado", "metodo_pago", "total", "creado"]
    list_filter = ["estado", "metodo_pago"]
    search_fields = ["cliente__username", "id"]
    inlines = [ItemPedidoInline]
    readonly_fields = ["subtotal", "descuento", "total", "creado"]


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "producto", "cantidad", "precio_unitario"]
    search_fields = ["pedido__id", "producto__nombre"]


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "estado", "fecha", "usuario"]
    list_filter = ["estado"]
    search_fields = ["pedido__id"]
    readonly_fields = ["fecha"]