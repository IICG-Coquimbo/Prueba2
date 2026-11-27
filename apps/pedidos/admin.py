from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "metodo_pago", "total", "creado")
    list_filter = ("estado", "metodo_pago", "creado")
    search_fields = ("=id", "cliente__username")
    list_select_related = ("cliente",)
    readonly_fields = ("estado", "creado")
    date_hierarchy = "creado"


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario")
    search_fields = ("=pedido__id", "producto__nombre")
    list_select_related = ("pedido", "producto")
    filter_horizontal = ("opciones",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "fecha", "usuario")
    list_filter = ("estado", "fecha")
    search_fields = ("=pedido__id", "usuario__username")
    list_select_related = ("pedido", "usuario")
    readonly_fields = ("pedido", "estado", "fecha", "usuario")
    actions = None

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("pedidos.view_historialestado")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
