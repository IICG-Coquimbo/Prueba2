"""Admin de la app pedidos segun docs/modelo_datos.md."""

from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


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
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = ("cliente__username", "id")
    list_editable = ("estado",)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("pedido__estado",)
    search_fields = ("producto__nombre", "pedido__id")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado", "fecha")
    search_fields = ("pedido__id", "estado")
