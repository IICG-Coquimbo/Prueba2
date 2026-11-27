from django import forms
from django.contrib.auth.models import User

from apps.pedidos.models import Pedido

from .models import Entrega


class EntregaForm(forms.ModelForm):
    """RF-14: asignar repartidor y registrar inicio/fin de la entrega."""

    class Meta:
        model = Entrega
        fields = ["pedido", "repartidor", "inicio", "fin"]
        labels = {
            "pedido": "Pedido",
            "repartidor": "Repartidor",
            "inicio": "Inicio",
            "fin": "Fin",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "repartidor": forms.Select(attrs={"class": "form-select"}),
            "inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "fin": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
        }
