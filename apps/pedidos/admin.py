from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    pass


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    pass


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    pass
