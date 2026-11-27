from django import forms
from django.core.exceptions import ValidationError
from apps.catalogo.models import OpcionProducto


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto:
            for tipo in [OpcionProducto.TIPO_TAMANO, OpcionProducto.TIPO_LECHE, OpcionProducto.TIPO_AZUCAR]:
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        label=dict(OpcionProducto.TIPOS).get(tipo, tipo),
                        queryset=opciones,
                        required=False,
                        widget=forms.Select(attrs={"class": "form-select"}),
                    )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Codigo de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo")
        return codigo.upper().strip()


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Direccion de entrega",
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=[
            ("efectivo", "Efectivo"),
            ("tarjeta", "Tarjeta"),
        ],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            from apps.cuentas.models import Direccion
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=[],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, siguiente_estado=None, **kwargs):
        super().__init__(*args, **kwargs)
        if siguiente_estado:
            from pedidos.models import ESTADOS_PEDIDO
            opciones = [e for e in ESTADOS_PEDIDO if e[0] == siguiente_estado]
            self.fields["estado"].choices = opciones
