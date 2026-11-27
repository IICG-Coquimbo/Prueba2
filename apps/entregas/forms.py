from django import forms
from .models import Entrega


class EntregaForm(forms.ModelForm):
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
            "inicio": forms.DateTimeInput(attrs={"class": "form-control"}),
            "fin": forms.DateTimeInput(attrs={"class": "form-control"}),
        }
