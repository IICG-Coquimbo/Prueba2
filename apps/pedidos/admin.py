from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    filter_horizontal = ("opciones",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "estado",
        "metodo_pago",
        "total",
        "creado",
    )
    search_fields = ("cliente__username", "id")
    list_filter = ("estado", "metodo_pago", "creado")
    inlines = (ItemPedidoInline,)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("producto__nombre", "pedido__id")
    list_filter = ("producto",)
    filter_horizontal = ("opciones",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    search_fields = ("pedido__id", "usuario__username")
    list_filter = ("estado", "fecha")
