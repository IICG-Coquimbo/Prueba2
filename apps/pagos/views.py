from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from apps.pagos.forms import PasarelaForm
from apps.pagos.models import Pago
from apps.pagos.servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = PasarelaForm
    template_name = "pagos/pasarela.html"
    permission_required = "pedidos.add_pedido"
    success_message = "Pago procesado."

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        context["titulo"] = "Pasarela de pago"
        context["boton_texto"] = "Procesar pago"
        return context

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            resultado_pago(self.pago.referencia, exitoso)
        except ValidationError as exc:
            for mensaje in exc.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        if exitoso:
            messages.success(self.request, "El pago fue aprobado.")
        else:
            messages.warning(self.request, "El pago fue rechazado. El pedido volvió al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})
