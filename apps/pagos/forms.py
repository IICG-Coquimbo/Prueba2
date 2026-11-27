from django import forms


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        choices=(
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ),
        label="Resultado del pago",
        widget=forms.RadioSelect,
    )
