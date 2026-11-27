from django.views.generic import FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect

from .forms import PasarelaForm
from .servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/pasarela.html"

    def dispatch(self, request, *args, **kwargs):
        self.referencia = kwargs.get("referencia")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.pagos.models import Pago
        pago = get_object_or_404(Pago, referencia=self.referencia)
        ctx["pago"] = pago
        return ctx

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            pago = resultado_pago(self.referencia, exitoso)
            if exitoso:
                messages.success(self.request, "Pago procesado con exito.")
            else:
                messages.error(self.request, "El pago fallo. El pedido vuelve al carrito.")
            return redirect("pedidos:pedido_detail", pk=pago.pedido_id)
        except Exception as exc:
            messages.error(self.request, str(exc))
            return redirect("pedidos:pedido_detail", pk=self.get_pedido_pk())

    def get_pedido_pk(self):
        from apps.pagos.models import Pago
        pago = get_object_or_404(Pago, referencia=self.referencia)
        return pago.pedido_id

    def get_success_url(self):
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.get_pedido_pk()})
