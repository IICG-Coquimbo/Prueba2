from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, FormView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect

from pagos.models import Pago
from pedidos.servicios import resultado_pago
from pedidos.forms import PasarelaForm


class PagoListView(PermissionRequiredMixin, ListView):
    """Historial de pagos del usuario."""
    model = Pago
    template_name = 'pagos/pago_list.html'
    permission_required = 'pagos.view_pago'
    context_object_name = 'pagos'

    def get_queryset(self):
        return Pago.objects.filter(pedido__cliente=self.request.user).order_by("-fecha")


class PasarelaFormView(PermissionRequiredMixin, FormView):
    """Vista de la pasarela de pago simulada."""
    form_class = PasarelaForm
    template_name = 'pagos/pasarela.html'
    permission_required = 'pagos.view_pago'
    success_url = reverse_lazy('pagos:pago_list')

    def form_valid(self, form):
        referencia = form.cleaned_data.get("referencia")
        if not referencia:
            form.add_error("referencia", "Falta la referencia del pago.")
            return self.form_invalid(form)
        # Buscar el pago asociado
        pago = get_object_or_404(Pago, referencia=referencia, estado="pendiente")
        # Determinar si fue exitoso o fallido según botón pulsado
        resultado = self.request.POST.get("resultado")
        if resultado == "exitoso":
            resultado_pago(referencia, exitoso=True)
        else:
            resultado_pago(referencia, exitoso=False)
        return super().form_valid(form)