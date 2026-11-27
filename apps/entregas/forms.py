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
            "inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
            "fin": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"},
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("inicio")
        fin = cleaned_data.get("fin")
        if inicio and fin and fin < inicio:
            self.add_error("fin", "La fecha de fin no puede ser anterior al inicio.")
        return cleaned_data
