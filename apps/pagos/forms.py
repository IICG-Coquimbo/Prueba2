from django import forms
from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["pedido", "metodo", "estado", "referencia", "monto", "fecha"]
        labels = {
            "pedido": "Pedido",
            "metodo": "Método",
            "estado": "Estado",
            "referencia": "Referencia",
            "monto": "Monto",
            "fecha": "Fecha",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
        }