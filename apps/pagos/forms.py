from django import forms

from .models import Pago


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        choices=[
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ],
        label="Resultado",
        widget=forms.RadioSelect(),
    )


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["pedido", "metodo", "estado", "referencia", "monto"]
        labels = {
            "pedido": "Pedido",
            "metodo": "Metodo",
            "estado": "Estado",
            "referencia": "Referencia",
            "monto": "Monto",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
        }
