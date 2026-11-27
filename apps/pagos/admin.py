from django.contrib import admin
from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("referencia", "pedido", "metodo", "estado", "monto", "fecha")
    list_filter = ("metodo", "estado", "fecha")
    search_fields = ("referencia", "pedido__id", "pedido__cliente__username")
    readonly_fields = ("fecha",)
    date_hierarchy = "fecha"