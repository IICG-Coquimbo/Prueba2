"""Admin de la app entregas segun docs/modelo_datos.md."""

from django.contrib import admin

from .models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "inicio", "fin", "minutos")
    list_filter = ("inicio", "fin")
    search_fields = ("pedido__id", "repartidor__username")
    readonly_fields = ("minutos",)
