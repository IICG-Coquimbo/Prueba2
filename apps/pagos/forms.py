from django import forms


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        label="Resultado",
        choices=[
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ],
        widget=forms.RadioSelect,
    )
