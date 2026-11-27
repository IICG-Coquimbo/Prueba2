from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PagoPasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"

    def get_form_kwargs(self):
        self.pago = get_object_or_404(
            Pago,
            referencia=self.kwargs["referencia"],
            pedido__cliente=self.request.user,
            metodo=Pago.Metodo.TARJETA,
        )
        return super().get_form_kwargs()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        context["titulo"] = "Pasarela de pago simulada"
        return context

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            self.pago = resultado_pago(self.pago.referencia, exitoso)
        except ValidationError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        if exitoso:
            messages.success(self.request, "Pago aprobado.")
        else:
            messages.error(self.request, "Pago fallido. Puedes intentar de nuevo.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})
