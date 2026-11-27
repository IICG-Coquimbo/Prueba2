from django import forms

from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "estado", "monto"]
        labels = {
            "metodo": "Método",
            "estado": "Estado",
            "monto": "Monto",
        }
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is not None and monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor que cero.")
        return monto
