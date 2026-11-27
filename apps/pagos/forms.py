from django import forms

from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["pedido", "metodo", "estado", "monto"]
        labels = {
            "pedido": "Pedido",
            "metodo": "Metodo",
            "estado": "Estado",
            "monto": "Monto",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        label="Resultado del pago",
        choices=[
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ],
        widget=forms.RadioSelect
    )
