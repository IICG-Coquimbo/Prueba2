from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from apps.pedidos.models import Pedido

from .models import Entrega

EN_PREPARACION = Pedido.Estado.EN_PREPARACION
LISTO_DESPACHO = Pedido.Estado.LISTO_DESPACHO
EN_CAMINO = Pedido.Estado.EN_CAMINO
ENTREGADO = Pedido.Estado.ENTREGADO


class EntregaAdmin(admin.ModelAdmin):
    list_display = ("pedido", "repartidor", "inicio", "fin", "minutos")
    list_filter = ("repartidor",)
    search_fields = ("pedido__pk",)


def _pedidos_repartidor():
    return (
        Pedido.objects.select_related("cliente", "direccion", "entrega", "cliente__perfil")
        .prefetch_related("items__producto", "items__opciones")
        .filter(estado__in=[EN_PREPARACION, LISTO_DESPACHO, EN_CAMINO, ENTREGADO])
        .distinct()
        .order_by("creado")
    )


def repartidor_admin_view(request):
    contexto = {
        **admin.site.each_context(request),
        "title": "Repartidor - pedidos",
        "object_list": _pedidos_repartidor(),
    }
    return TemplateResponse(request, "admin/entregas_repartidor.html", contexto)


admin.site.register(Entrega, EntregaAdmin)

_original_get_urls = admin.site.get_urls


def _get_urls():
    custom = [
        path(
            "repartidor/",
            admin.site.admin_view(repartidor_admin_view),
            name="entregas_repartidor",
        ),
    ]
    return custom + _original_get_urls()


admin.site.get_urls = _get_urls
