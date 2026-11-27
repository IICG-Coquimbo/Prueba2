from django.contrib import admin

from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "inicio", "fin", "minutos")
    list_filter = ("repartidor",)
    search_fields = ("repartidor__username",)
