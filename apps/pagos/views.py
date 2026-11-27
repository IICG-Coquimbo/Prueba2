from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"

    def get_pago(self):
        return get_object_or_404(
            Pago,
            referencia=self.kwargs["referencia"],
            pedido__cliente=self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.get_pago()
        return context

    def form_valid(self, form):
        try:
            pago = resultado_pago(
                self.kwargs["referencia"],
                form.cleaned_data["resultado"] == "exitoso",
            )
        except ValidationError as error:
            mensaje = error.messages[0] if getattr(error, "messages", None) else str(error)
            form.add_error(None, mensaje)
            return self.form_invalid(form)
        if pago.estado == Pago.Estado.EXITOSO:
            messages.success(self.request, "Pago aprobado. El pedido fue recibido.")
        else:
            messages.warning(self.request, "Pago fallido. El pedido volvio al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        pago = self.get_pago()
        return reverse("pedidos:pedido_detail", args=[pago.pedido_id])
