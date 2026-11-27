from django.contrib import admin
from .models import Pedido, ItemPedido, HistorialEstado


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("precio_unitario",)


class HistorialEstadoInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ("fecha", "usuario")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "metodo_pago", "total", "creado")
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = ("cliente__username", "cliente__email", "id")
    readonly_fields = ("creado", "subtotal", "descuento", "total")
    inlines = [ItemPedidoInline, HistorialEstadoInline]
    date_hierarchy = "creado"


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("producto__categoria",)
    search_fields = ("pedido__id", "producto__nombre")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado",)
    search_fields = ("pedido__id", "usuario__username")
    readonly_fields = ("fecha",)
    date_hierarchy = "fecha"