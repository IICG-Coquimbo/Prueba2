from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.pagos.forms import PasarelaForm
from apps.pagos.models import Pago
from apps.pagos.servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/pasarela.html"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        return context

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            resultado_pago(self.pago.referencia, exitoso)
        except ValidationError as error:
            form.add_error(None, error.message)
            return self.form_invalid(form)
        messages.success(self.request, "Pago procesado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido.pk})
