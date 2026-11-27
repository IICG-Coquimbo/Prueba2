from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "total", "creado")
    list_filter = ("estado", "metodo_pago")


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    filter_horizontal = ("opciones",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado",)
