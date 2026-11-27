from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import PasarelaForm
from .models import Pago
from .servicios import resultado_pago


class PasarelaView(PermissionRequiredMixin, FormView):
    """
    Vista de la pasarela de pago simulada.
    Muestra el monto y la referencia, y permite elegir
    entre 'Pago exitoso' y 'Pago fallido'.
    """
    template_name = 'pagos/pasarela.html'
    form_class = PasarelaForm
    permission_required = 'pedidos.add_pedido'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasa la referencia desde la URL al formulario (aunque no es un campo del form)
        kwargs['referencia'] = self.kwargs.get('referencia')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referencia = self.kwargs.get('referencia')
        pago = get_object_or_404(Pago, referencia=referencia)
        context['pago'] = pago
        return context

    def form_valid(self, form):
        referencia = self.kwargs.get('referencia')
        exitoso = form.cleaned_data['resultado'] == 'exitoso'

        try:
            resultado_pago(referencia, exitoso)
            if exitoso:
                messages.success(self.request, 'El pago se procesó correctamente.')
            else:
                messages.warning(self.request, 'El pago fue rechazado. El pedido vuelve al carrito.')
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # Redirige al detalle del pedido
        pago = get_object_or_404(Pago, referencia=referencia)
        return redirect('pedidos:pedido_detail', pk=pago.pedido.pk)