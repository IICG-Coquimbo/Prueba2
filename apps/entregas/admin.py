from django.contrib import admin
from apps.entregas.models import Entrega


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ["pedido", "repartidor", "inicio", "fin", "minutos"]
    list_filter = ["repartidor"]
    search_fields = ["pedido__id", "repartidor__username"]
    readonly_fields = ["minutos"]