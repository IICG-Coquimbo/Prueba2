from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from apps.pagos.forms import PasarelaForm
from apps.pagos.models import Pago
from apps.pagos.servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, LoginRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=self.kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        return context

    def form_valid(self, form):
        try:
            self.pago = resultado_pago(
                self.pago.referencia, form.cleaned_data["resultado"] == "exitoso"
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if self.pago.estado == "exitoso":
            messages.success(self.request, "Pago aprobado correctamente.")
        else:
            messages.error(self.request, "Pago fallido: el pedido volvió al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", args=[self.pago.pedido_id])
