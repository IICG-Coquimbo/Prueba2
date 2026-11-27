from django import forms

from apps.cuentas.models import Direccion

from .models import Pedido


class CodigoForm(forms.Form):
    texto = forms.CharField(
        label="Codigo de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class QuitarItemForm(forms.Form):
    pass


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Direccion",
        empty_label="(selecciona una direccion)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=Pedido.MetodoPago.choices,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=[],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, pedido=None, permitidos=None, **kwargs):
        super().__init__(*args, **kwargs)
        permitidos = permitidos or []
        self.fields["estado"].choices = [
            (e.value, e.label) for e in Pedido.Estado if e.value in permitidos
        ]
