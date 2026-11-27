from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from entregas.models import Entrega
from users.models import User  # User model


class EntregaListView(PermissionRequiredMixin, ListView):
    """Lista de entregas vista según el rol del usuario."""
    model = Entrega
    template_name = 'entregas/entrega_list.html'
    permission_required = 'entregas.view_entrega'
    context_object_name = 'entregas'

    def get_queryset(self):
        usuario = self.request.user
        # Dueno/Administrador ven todas; Repartidor solo las suyas; Cliente solo las suyas (via pedido)
        if usuario.is_staff:
            return Entrega.objects.all()
        # Repartidor: solo las que tiene asignadas
        if hasattr(usuario, 'groups') and usuario.groups.filter(name='Repartidor').exists():
            return Entrega.objects.filter(repartidor=usuario)
        # Cliente: entregas de sus pedidos
        return Entrega.objects.filter(pedido__cliente=usuario)


class EntregaDetailView(PermissionRequiredMixin, DetailView):
    """Detalle de una entrega."""
    model = Entrega
    template_name = 'entregas/entrega_detail.html'
    permission_required = 'entregas.view_entrega'
    context_object_name = 'entrega'


class EntregaAssignView(PermissionRequiredMixin, SuccessMessageMixin, FormView):
    """Asignar un repartidor a una entrega (solo para admin/dueño)."""
    template_name = 'entregas/entrega_assign.html'
    permission_required = 'entregas.change_entrega'
    success_url = reverse_lazy('entregas:list')
    success_message = "Repartidor asignado correctamente."
    form_class = None  # we'll define form class dynamically

    def dispatch(self, request, *args, **kwargs):
        self.entrega = get_object_or_404(Entrega, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        from django import forms
        class AsignarRepartidorForm(forms.Form):
            repartidor = forms.ModelChoiceField(
                label="Repartidor",
                queryset=User.objects.filter(groups__name="Repartidor"),
                widget=forms.Select(attrs={"class": "form-select"}),
            )
        return AsignarRepartidorForm

    def form_valid(self, form):
        repartidor = form.cleaned_data["repartidor"]
        self.entrega.repartidor = repartidor
        self.entrega.inicio = timezone.now()
        self.entrega.save()
        return super().form_valid(form)