from django import forms
from django.contrib.auth.models import User

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
            "inicio": forms.TextInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "fin": forms.TextInput(attrs={"class": "form-control", "type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["repartidor"].queryset = User.objects.all()

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("inicio")
        fin = cleaned.get("fin")
        if inicio and fin and fin < inicio:
            self.add_error("fin", "La fecha de fin no puede ser anterior a la de inicio.")
        return cleaned
