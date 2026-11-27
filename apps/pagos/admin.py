from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("referencia", "pedido", "metodo", "estado", "monto", "fecha")
    list_filter = ("metodo", "estado", "fecha")
    search_fields = ("=referencia", "=pedido__id")
    list_select_related = ("pedido",)
    readonly_fields = ("estado", "fecha")
