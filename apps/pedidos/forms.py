from django import forms
from django.forms import ModelChoiceField, RadioSelect, Select

from .models import ItemPedido, Pedido


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={"class": "form-control"}))

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        if producto:
            for tipo in ("tamano", "leche", "azucar"):
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        queryset=opciones,
                        required=False,
                        empty_label=f"Sin {tipo}",
                        widget=forms.Select(attrs={"class": "form-select"}),
                    )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Codigo de descuento"}))


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=Pedido.METODO_PAGO_CHOICES,
        widget=RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            from apps.cuentas.models import Direccion
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(choices=[], widget=RadioSelect)

    def __init__(self, *args, estados=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estados:
            self.fields["estado"].choices = [(e, e) for e in estados]


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        choices=[("exitoso", "Pago exitoso"), ("fallido", "Pago fallido")],
        widget=RadioSelect,
        initial="exitoso",
    )
