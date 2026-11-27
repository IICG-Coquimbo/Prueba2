from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 1
    filter_horizontal = ("opciones",)


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "total", "creado")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("cliente__username",)
    inlines = [ItemPedidoInline, HistorialEstadoInline]


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("producto__nombre",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado",)
