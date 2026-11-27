from django import forms

from apps.pagos.models import Pago

RESULTADO_PAGO_OPCIONES = [
    ("exitoso", "Pago exitoso"),
    ("fallido", "Pago fallido"),
]


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "estado", "referencia", "monto"]
        labels = {
            "metodo": "Método de pago",
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
        choices=RESULTADO_PAGO_OPCIONES,
        widget=forms.RadioSelect,
    )
