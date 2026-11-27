from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.pagos.servicios import resultado_pago

from .forms import PasarelaForm
from .models import Pago


class PasarelaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = "pagos/accion_form.html"
    form_class = PasarelaForm
    permission_required = "pedidos.add_pedido"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        context["titulo"] = "Pasarela"
        return context

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            pago = resultado_pago(
                self.pago.referencia,
                form.cleaned_data["resultado"] == "exitoso",
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Pago resuelto.")
        return redirect(reverse("pedidos:pedido_detail", args=[pago.pedido_id]))
