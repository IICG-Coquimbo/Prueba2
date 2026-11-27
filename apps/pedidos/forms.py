from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion
from apps.pedidos.models import HistorialEstado, ItemPedido, Pedido
from apps.promociones.models import CodigoDescuento

METODO_PAGO_OPCIONES = [
    ("efectivo", "Efectivo"),
    ("tarjeta", "Tarjeta"),
]


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "estado",
            "direccion",
            "metodo_pago",
            "codigo_descuento",
        ]
        labels = {
            "estado": "Estado",
            "direccion": "Dirección de entrega",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
        }
        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
        }


class ItemPedidoForm(forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = ["producto", "cantidad", "opciones"]
        labels = {
            "producto": "Producto",
            "cantidad": "Cantidad",
            "opciones": "Opciones",
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "opciones": forms.CheckboxSelectMultiple(),
        }


class HistorialEstadoForm(forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["estado", "usuario"]
        labels = {
            "estado": "Estado",
            "usuario": "Usuario",
        }
        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
        }


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = OpcionProducto.objects.filter(producto=producto)
        tipos = ["tamano", "leche", "azucar"]
        for tipo in tipos:
            qs = opciones.filter(tipo=tipo)
            if qs.exists():
                self.fields[f"opcion_{tipo}"] = forms.ChoiceField(
                    label=tipo.capitalize(),
                    required=False,
                    choices=[(o.id, o.nombre) for o in qs],
                    widget=forms.Select(attrs={"class": "form-select"}),
                )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Dirección de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=METODO_PAGO_OPCIONES,
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(
            usuario=usuario
        )

    def clean(self):
        cleaned_data = super().clean()
        direccion = cleaned_data.get("direccion")
        metodo_pago = cleaned_data.get("metodo_pago")
        if not direccion:
            self.add_error(
                "direccion", "Debes seleccionar una dirección de entrega."
            )
        if not metodo_pago:
            self.add_error(
                "metodo_pago", "Debes seleccionar un método de pago."
            )
        return cleaned_data


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=[],
        widget=forms.RadioSelect,
    )

    def __init__(self, opciones_estado, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = opciones_estado
