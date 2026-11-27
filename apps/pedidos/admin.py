from django.contrib import admin
from .models import Pedido, ItemPedido, HistorialEstado


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "estado",
        "metodo_pago",
        "subtotal",
        "descuento",
        "total",
        "creado",
    )
    list_filter = ("estado", "metodo_pago")
    search_fields = ("cliente__username", "id")
    readonly_fields = ("creado",)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("pedido__id", "producto__nombre")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    search_fields = ("pedido__id", "estado")