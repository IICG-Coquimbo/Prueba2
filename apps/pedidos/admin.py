from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "estado",
        "direccion",
        "metodo_pago",
        "codigo_descuento",
        "subtotal",
        "descuento",
        "total",
        "creado",
    )
    search_fields = ("id", "cliente__username", "cliente__first_name", "cliente__last_name")
    list_filter = ("estado", "metodo_pago", "creado")


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("pedido__id", "producto__nombre")
    list_filter = ("producto",)
    filter_horizontal = ("opciones",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    search_fields = ("pedido__id", "usuario__username")
    list_filter = ("estado", "fecha")
