"""Admin de la app promociones segun docs/modelo_datos.md."""

from django.contrib import admin

from .models import CodigoDescuento


@admin.register(CodigoDescuento)
class CodigoDescuentoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "porcentaje",
        "vigente_desde",
        "vigente_hasta",
        "solo_primer_pedido",
        "activo",
    )
    list_filter = ("activo", "solo_primer_pedido", "vigente_desde", "vigente_hasta")
    search_fields = ("codigo",)
