from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import FormView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.pagos.models import Pago
from apps.pagos.forms import PasarelaForm
from apps.pagos.servicios import resultado_pago


class PasarelaView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = "pagos/pasarela.html"
    form_class = PasarelaForm
    permission_required = "pedidos.add_pedido"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["referencia"] = self.kwargs["referencia"]
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pago"] = get_object_or_404(Pago, referencia=self.kwargs["referencia"])
        return context

    def form_valid(self, form):
        referencia = self.kwargs["referencia"]
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        try:
            resultado_pago(referencia, exitoso)
            if exitoso:
                messages.success(self.request, "Pago procesado correctamente. Pedido recibido.")
            else:
                messages.error(self.request, "Pago fallido. El pedido volvio al carrito.")
        except Exception as e:
            messages.error(self.request, str(e))
        return redirect("pedidos:pedido_detail", pk=get_object_or_404(Pago, referencia=referencia).pedido.pk)