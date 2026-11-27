from django.contrib import admin
from .models import CodigoDescuento


@admin.register(CodigoDescuento)
class CodigoDescuentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "porcentaje", "vigente_desde", "vigente_hasta", "activo")
    list_filter = ("activo", "vigente_desde")
    search_fields = ("codigo",)