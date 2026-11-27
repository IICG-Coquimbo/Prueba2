from django import forms

from apps.entregas.models import Entrega


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ["repartidor", "inicio", "fin"]
        labels = {
            "repartidor": "Repartidor",
            "inicio": "Inicio",
            "fin": "Fin",
        }
        widgets = {
            "repartidor": forms.Select(attrs={"class": "form-select"}),
            "inicio": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
        }
