from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion

from .models import Pedido


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        initial=1,
        min_value=1,
        label='Cantidad',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        opciones = (
            ('opcion_tamano', 'tamano', 'Tamano'),
            ('opcion_leche', 'leche', 'Leche'),
            ('opcion_azucar', 'azucar', 'Azucar'),
        )
        for nombre, tipo, etiqueta in opciones:
            self.fields[nombre] = forms.ModelChoiceField(
                queryset=OpcionProducto.objects.filter(producto=producto, tipo=tipo),
                required=False,
                empty_label='Sin variante',
                label=etiqueta,
                widget=forms.Select(attrs={'class': 'form-select'}),
            )

    def opciones_seleccionadas(self):
        cleaned_data = getattr(self, 'cleaned_data', {})
        return [
            cleaned_data[nombre]
            for nombre in ('opcion_tamano', 'opcion_leche', 'opcion_azucar')
            if cleaned_data.get(nombre)
        ]


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    texto = forms.CharField(
        max_length=20,
        label='Codigo de descuento',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )


class ConfirmarPedidoForm(forms.Form):
    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['direccion'] = forms.ModelChoiceField(
            queryset=Direccion.objects.filter(usuario=usuario),
            label='Direccion de entrega',
            widget=forms.Select(attrs={'class': 'form-select'}),
        )
        self.fields['metodo_pago'] = forms.ChoiceField(
            choices=Pedido.MetodoPago.choices,
            label='Metodo de pago',
            widget=forms.RadioSelect,
        )


class EstadoPedidoForm(forms.Form):
    def __init__(self, opciones, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'] = forms.ChoiceField(
            choices=opciones,
            label='Nuevo estado',
            widget=forms.RadioSelect,
        )
