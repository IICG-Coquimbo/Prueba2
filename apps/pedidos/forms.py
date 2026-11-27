from django import forms

from apps.cuentas.models import Direccion

from .models import Pedido


TIPOS_OPCION = ("tamano", "leche", "azucar")

ETIQUETAS_ESTADO = {
    "carrito": "Carrito",
    "pendiente_pago": "Pendiente de pago",
    "recibido": "Recibido",
    "en_preparacion": "En preparación",
    "listo_despacho": "Listo para despacho",
    "en_camino": "En camino",
    "entregado": "Entregado",
}


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    tamano = forms.ChoiceField(
        required=False,
        label="Tamaño",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    leche = forms.ChoiceField(
        required=False,
        label="Leche",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    azucar = forms.ChoiceField(
        required=False,
        label="Azúcar",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for tipo in TIPOS_OPCION:
            opciones = producto.opciones.filter(tipo=tipo)
            self.fields[tipo].choices = [("", "---------")] + [
                (opcion.pk, opcion.nombre) for opcion in opciones
            ]


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Código de descuento",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Dirección",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=Pedido.MetodoPago.choices,
        label="Método de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Estado",
        widget=forms.RadioSelect,
    )

    def __init__(self, estados, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = [
            (estado, ETIQUETAS_ESTADO.get(estado, estado)) for estado in estados
        ]
