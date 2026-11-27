from django import forms

from .models import Entrega


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ["repartidor"]
        labels = {"repartidor": "Repartidor"}
        widgets = {
            "repartidor": forms.Select(attrs={"class": "form-select"}),
        }
