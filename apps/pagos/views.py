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
    permission_required = 'pedidos.add_pedido'
    form_class = PasarelaForm
    template_name = 'pagos/accion_form.html'

    def get_pago(self):
        if not hasattr(self, 'pago'):
            self.pago = get_object_or_404(
                Pago,
                referencia=self.kwargs['referencia'],
                pedido__cliente=self.request.user,
            )
        return self.pago

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Pasarela de pago simulada'
        context['pago'] = self.get_pago()
        return context

    def form_valid(self, form):
        pago = self.get_pago()
        try:
            resultado_pago(pago.referencia, form.cleaned_data['resultado'])
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)

        if form.cleaned_data['resultado'] == 'exitoso':
            messages.success(self.request, 'Pago exitoso. El pedido fue confirmado.')
        else:
            messages.warning(self.request, 'Pago fallido. El pedido volvio al carrito.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pedidos:pedido_detail', args=[self.get_pago().pedido_id])
