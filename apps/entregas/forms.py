"""Formularios de la app entregas segun docs/reglas_formularios.md."""

from django import forms

from .models import Entrega


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
