from django.contrib import admin

from apps.pagos.models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("referencia", "pedido", "metodo", "estado", "monto", "fecha")
    list_filter = ("metodo", "estado")
    search_fields = ("referencia", "pedido__id")
