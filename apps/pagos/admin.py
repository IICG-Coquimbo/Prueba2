from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "metodo", "estado", "monto", "referencia")
    list_filter = ("metodo", "estado")
    search_fields = ("referencia",)
