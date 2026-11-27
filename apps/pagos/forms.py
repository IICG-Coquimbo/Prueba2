from django import forms

from apps.pagos.models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "monto", "referencia"]
        labels = {
            "metodo": "Metodo",
            "monto": "Monto",
            "referencia": "Referencia",
        }
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is not None and monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor a cero.")
        return monto


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        label="Resultado",
        choices=[("exitoso", "Pago exitoso"), ("fallido", "Pago fallido")],
        widget=forms.RadioSelect,
    )
