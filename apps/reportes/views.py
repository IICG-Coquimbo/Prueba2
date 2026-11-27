from decimal import Decimal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from apps.entregas.models import Entrega
from apps.pedidos.models import ItemPedido, Pedido


ESTADOS_VENTA = [
    Pedido.Estado.RECIBIDO,
    Pedido.Estado.EN_PREPARACION,
    Pedido.Estado.LISTO_DESPACHO,
    Pedido.Estado.EN_CAMINO,
    Pedido.Estado.ENTREGADO,
]


class ReportePanelView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_semana = hoy - timezone.timedelta(days=6)
        pedidos_validos = Pedido.objects.filter(estado__in=ESTADOS_VENTA)
        total_decimal = DecimalField(max_digits=10, decimal_places=2)
        context["ventas_hoy"] = pedidos_validos.filter(creado__date=hoy).aggregate(
            total=Coalesce(Sum("total"), Value(Decimal("0.00")), output_field=total_decimal)
        )["total"]
        context["ventas_semana"] = pedidos_validos.filter(creado__date__gte=inicio_semana).aggregate(
            total=Coalesce(Sum("total"), Value(Decimal("0.00")), output_field=total_decimal)
        )["total"]
        context["productos_mas_pedidos"] = (
            ItemPedido.objects.filter(pedido__estado__in=ESTADOS_VENTA)
            .values("producto__nombre")
            .annotate(unidades=Sum("cantidad"))
            .order_by("-unidades", "producto__nombre")[:5]
        )
        return context


class ReporteRepartidoresView(PermissionRequiredMixin, TemplateView):
    permission_required = "pedidos.ver_reportes"
    template_name = "reportes/repartidores.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entregas = (
            Entrega.objects.filter(fin__isnull=False)
            .values("repartidor__first_name", "repartidor__username")
            .annotate(entregas=Count("id"))
            .order_by("-entregas")
        )
        ranking = []
        for e in entregas:
            qs = Entrega.objects.filter(
                repartidor__username=e["repartidor__username"], fin__isnull=False
            )
            total_min = 0
            count = 0
            for entrega in qs:
                minutos = entrega.minutos
                if minutos is not None:
                    total_min += minutos
                    count += 1
            promedio = round(total_min / count, 2) if count else None
            ranking.append({
                "nombre": e["repartidor__first_name"] or e["repartidor__username"],
                "entregas": e["entregas"],
                "promedio": promedio,
            })
        context["ranking"] = ranking
        return context
