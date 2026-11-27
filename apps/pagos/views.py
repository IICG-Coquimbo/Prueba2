from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import EstadoPago, Pago
from .servicios import resultado_pago


class PagoPasarelaView(PermissionRequiredMixin, FormView):
    """Pasarela simulada: solo elige el resultado, nunca pide datos de tarjeta (RNF-03)."""

    template_name = "pagos/pasarela.html"
    form_class = PasarelaForm
    permission_required = "pedidos.add_pedido"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(
            Pago,
            referencia=kwargs["referencia"],
            pedido__cliente=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        return context

    def form_valid(self, form):
        try:
            self.pago = resultado_pago(
                self.kwargs["referencia"], form.cleaned_data["resultado"]
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        if self.pago.estado == EstadoPago.EXITOSO:
            messages.success(self.request, "Pago aprobado. Su pedido fue recibido.")
        else:
            messages.warning(self.request, "Pago fallido. Su pedido volvió al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id}
        )
