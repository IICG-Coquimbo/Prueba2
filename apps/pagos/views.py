from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, TemplateView

from .models import Pago


class PagoRealizadoView(TemplateView):
    template_name = "pagos/realizado.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referencia = self.request.GET.get("referencia")
        if referencia:
            try:
                pago = Pago.objects.get(referencia=referencia)
                context["pago"] = pago
            except Pago.DoesNotExist:
                context["pago"] = None
        else:
            context["pago"] = None
        return context


class PagoFallidoView(TemplateView):
    template_name = "pagos/fallido.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referencia = self.request.GET.get("referencia")
        if referencia:
            try:
                pago = Pago.objects.get(referencia=referencia)
                context["pago"] = pago
            except Pago.DoesNotExist:
                context["pago"] = None
        else:
            context["pago"] = None
        return context


class PagoDetalleView(DetailView):
    model = Pago
    template_name = "pagos/detalle.html"
    context_object_name = "pago"

    def get_queryset(self):
        return Pago.objects.select_related("pedido__cliente", "pedido")