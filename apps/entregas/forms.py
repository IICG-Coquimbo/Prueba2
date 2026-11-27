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
            "inicio": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "fin": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("inicio")
        fin = cleaned.get("fin")
        if inicio and fin and fin < inicio:
            self.add_error("fin", "La fecha fin no puede ser anterior a la fecha inicio.")
        return cleaned
