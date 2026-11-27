from django import forms


class PasarelaForm(forms.Form):
    RESULTADO_CHOICES = [
        ("exitoso", "Pago exitoso"),
        ("fallido", "Pago fallido"),
    ]
    resultado = forms.ChoiceField(
        choices=RESULTADO_CHOICES,
        label="Resultado del pago",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )