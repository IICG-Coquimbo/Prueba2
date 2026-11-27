from django.contrib import admin

from .models import CodigoDescuento


@admin.register(CodigoDescuento)
class CodigoDescuentoAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "porcentaje",
        "vigente_desde",
        "vigente_hasta",
        "activo",
    ]
    list_filter = ["activo", "solo_primer_pedido"]
    search_fields = ["codigo"]
