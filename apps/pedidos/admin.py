from django.contrib import admin
from .models import Pedido, ItemPedido, HistorialEstado, EstadoPedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("pk", "cliente", "estado", "metodo_pago", "total", "creado")
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = ("cliente__username", "pk")
    readonly_fields = ("creado",)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("pedido__pk", "producto__nombre")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado", "fecha")
    search_fields = ("pedido__pk", "usuario__username")