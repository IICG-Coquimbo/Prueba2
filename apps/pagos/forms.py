from django import forms

from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["pedido", "metodo", "estado", "referencia", "monto"]
        labels = {
            "pedido": "Pedido",
            "metodo": "Método",
            "estado": "Estado",
            "referencia": "Referencia",
            "monto": "Monto",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor que cero.")
        return monto


class PasarelaForm(forms.Form):
    """Pasarela simulada: no pide ni guarda números de tarjeta (RNF-03)."""

    RESULTADOS = [
        ("exitoso", "Pago exitoso"),
        ("fallido", "Pago fallido"),
    ]

    resultado = forms.ChoiceField(
        label="Resultado del pago",
        choices=RESULTADOS,
        widget=forms.RadioSelect,
        error_messages={"required": "Seleccione el resultado del pago."},
    )
