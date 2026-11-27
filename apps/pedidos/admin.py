from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


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
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = (
        "cliente__username",
        "cliente__email",
        "direccion__alias",
        "codigo_descuento__codigo",
    )
    list_select_related = ("cliente", "direccion", "codigo_descuento")


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    list_filter = ("producto", "pedido__estado")
    search_fields = ("producto__nombre", "pedido__cliente__username")
    filter_horizontal = ("opciones",)
    list_select_related = ("pedido", "producto")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado", "fecha")
    search_fields = ("pedido__cliente__username", "usuario__username")
    list_select_related = ("pedido", "usuario")
