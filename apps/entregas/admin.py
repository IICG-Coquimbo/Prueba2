from django.contrib import admin

from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "inicio", "fin")
    search_fields = ("pedido__id", "repartidor__username")
    list_filter = ("inicio", "fin")
