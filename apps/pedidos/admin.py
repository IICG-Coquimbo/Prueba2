from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("pk", "cliente", "estado", "metodo_pago", "total", "creado")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("cliente__username", "pk")


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("pedido__estado",)
    search_fields = ("producto__nombre", "pedido__pk")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado",)
    search_fields = ("pedido__pk", "usuario__username")
