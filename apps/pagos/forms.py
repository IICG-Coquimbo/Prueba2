"""Formularios de la app pagos segun docs/reglas_formularios.md y docs/reglas_flujo.md."""

from django import forms

from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "estado", "referencia", "monto"]
        labels = {
            "metodo": "Metodo",
            "estado": "Estado",
            "referencia": "Referencia",
            "monto": "Monto",
        }
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        label="Resultado del pago",
        choices=[
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ],
        widget=forms.RadioSelect,
    )
