from django import forms
from django.core.exceptions import ValidationError
from .models import Pago
from apps.pedidos.models import Pedido


class PasarelaForm(forms.Form):
    """
    Formulario para la pasarela de pago simulada.
    Permite elegir entre 'Pago exitoso' y 'Pago fallido'.
    """
    RESULTADO_CHOICES = [
        ('exitoso', 'Pago exitoso'),
        ('fallido', 'Pago fallido'),
    ]
    resultado = forms.ChoiceField(
        choices=RESULTADO_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Resultado de la simulación',
    )


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ["metodo", "monto"]
        labels = {
            "metodo": "Método de pago",
            "monto": "Monto",
        }
        widgets = {
            "metodo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        pedido = kwargs.pop("pedido", None)
        super().__init__(*args, **kwargs)

        # El monto es de solo lectura y se calcula del pedido
        self.fields["monto"].widget.attrs["readonly"] = True

        if pedido:
            self.fields["monto"].initial = pedido.total

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is not None and monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor a 0.")
        return monto

    def clean(self):
        cleaned_data = super().clean()
        metodo = cleaned_data.get("metodo")
        monto = cleaned_data.get("monto")

        # Validar que no se pida número de tarjeta (RNF-03)
        # El modelo Pago no tiene campo para número de tarjeta
        if metodo == Pago.Metodo.TARJETA:
            # En un caso real, aquí se integraría con pasarela de pagos
            # No almacenamos datos de tarjeta
            pass

        return cleaned_data