from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pago"] = self.pago
        return ctx

    def form_valid(self, form):
        try:
            pago = resultado_pago(self.pago.referencia, form.cleaned_data["resultado"] == "exitoso")
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.form_invalid(form)
        if pago.estado == Pago.Estado.EXITOSO:
            messages.success(self.request, "Pago exitoso.")
        else:
            messages.error(self.request, "Pago fallido.")
        return redirect(reverse("pedidos:pedido_detail", args=[pago.pedido_id]))
