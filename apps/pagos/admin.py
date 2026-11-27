from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "metodo", "estado", "referencia", "monto", "fecha")
    list_filter = ("metodo", "estado", "fecha")
    search_fields = ("referencia", "pedido__id")
