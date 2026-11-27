from django import forms

from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo"]
        labels = {"metodo": "Metodo de pago"}
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
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
