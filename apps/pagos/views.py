from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.pagos.forms import PasarelaForm
from apps.pagos.models import Pago
from apps.pagos.servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(
            Pago,
            referencia=self.kwargs["referencia"],
            pedido__cliente=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = self.pago
        return context

    def form_valid(self, form):
        try:
            resultado_pago(self.kwargs["referencia"], form.cleaned_data["resultado"] == "exitoso")
        except ValidationError as e:
            form.add_error(None, str(e.message if hasattr(e, "message") else "; ".join(e.messages)))
            return self.form_invalid(form)
        if form.cleaned_data["resultado"] == "exitoso":
            messages.success(self.request, "Pago aprobado.")
        else:
            messages.error(self.request, "Pago fallido. El pedido volvio al carrito.")
        return redirect("pedidos:pedido_detail", pk=self.pago.pedido_id)
