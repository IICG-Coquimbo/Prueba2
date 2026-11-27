from django.contrib import admin

from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "inicio", "fin", "minutos")
    list_filter = ("inicio", "fin", "repartidor")
    search_fields = ("pedido__cliente__username", "repartidor__username")
    list_select_related = ("pedido", "repartidor")
