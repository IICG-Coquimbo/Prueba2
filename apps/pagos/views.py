from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import FormView

from apps.pedidos.models import Pedido

from . import servicios
from .forms import PasarelaForm
from .models import Pago


class PagoPasarelaView(PermissionRequiredMixin, FormView):
    permission_required = "pedidos.add_pedido"
    form_class = PasarelaForm
    template_name = "pagos/accion_form.html"

    @cached_property
    def pago(self):
        return get_object_or_404(
            Pago.objects.select_related("pedido"),
            referencia=self.kwargs["referencia"],
            pedido__cliente=self.request.user,
            metodo=Pedido.MetodoPago.TARJETA,
            estado=Pago.Estado.PENDIENTE,
            pedido__estado=Pedido.Estado.PENDIENTE_PAGO,
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "pago": self.pago, "usuario": self.request.user}

    def get_context_data(self, **kwargs):
        return super().get_context_data(monto=self.pago.monto, **kwargs)

    def form_valid(self, form):
        exitoso = form.cleaned_data["resultado"]
        try:
            servicios.resultado_pago(self.pago.referencia, exitoso)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)

        if exitoso:
            messages.success(self.request, "Pago aprobado. Tu pedido fue recibido.")
        else:
            messages.error(self.request, "Pago fallido. Tu pedido volvió al carrito.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pago.pedido_id})
