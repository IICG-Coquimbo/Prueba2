from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/pasarela.html"

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(Pago, referencia=kwargs["referencia"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pago"] = self.pago
        return ctx

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            resultado_pago(self.pago.referencia, exitoso)
        except ValidationError as e:
            form.add_error(None, e.messages[0])
            return self.form_invalid(form)
        return redirect("pedidos:pedido_detail", pk=self.pago.pedido.pk)

    def get_success_url(self):
        from django.urls import reverse_lazy
        return reverse_lazy("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido.pk})
