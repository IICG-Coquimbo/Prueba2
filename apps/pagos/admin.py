from django.contrib import admin
from apps.pagos.models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ["pedido", "metodo", "estado", "referencia", "monto", "fecha"]
    list_filter = ["metodo", "estado"]
    search_fields = ["pedido__id", "referencia"]
    readonly_fields = ["fecha"]