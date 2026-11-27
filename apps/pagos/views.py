from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"
    permission_required = "pedidos.add_pedido"
    raise_exception = True
    extra_context = {
        "titulo": "Pasarela de pago simulada",
        "accion": "Confirmar pago",
    }

    def get_pago(self):
        if not hasattr(self, "pago"):
            queryset = Pago.objects.select_related("pedido")
            if not (
                self.request.user.has_perm("pedidos.ver_reportes")
                or self.request.user.is_staff
            ):
                queryset = queryset.filter(pedido__cliente=self.request.user)
            self.pago = get_object_or_404(
                queryset, referencia=self.kwargs["referencia"]
            )
        return self.pago

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.get_pago()
        context["pago"] = self.pago
        context["pedido"] = self.pago.pedido
        return context

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"] == "exitoso"
        referencia = self.get_pago().referencia
        try:
            self.pago = resultado_pago(referencia, exitoso=exitoso)
        except ValidationError as error:
            form.add_error(None, error.messages)
            return self.form_invalid(form)
        self.success_message = (
            "Pago aprobado. Tu pedido fue recibido."
            if exitoso
            else "Pago fallido. Tu pedido volvió al carrito."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})
