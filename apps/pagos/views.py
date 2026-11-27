"""Vistas de la app pagos segun docs/reglas_vistas_templates.md y docs/reglas_flujo.md."""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    form_class = PasarelaForm
    template_name = "pagos/pasarela.html"
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referencia = self.kwargs["referencia"]
        context["pago"] = get_object_or_404(Pago, referencia=referencia)
        return context

    def form_valid(self, form):
        referencia = self.kwargs["referencia"]
        self.pago = get_object_or_404(Pago, referencia=referencia)
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            resultado_pago(referencia, exitoso)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido.pk})
