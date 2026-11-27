from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion

from .models import HistorialEstado, ItemPedido, Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["direccion", "metodo_pago", "codigo_descuento"]
        labels = {
            "direccion": "Direccion",
            "metodo_pago": "Metodo de pago",
            "codigo_descuento": "Codigo de descuento",
        }
        widgets = {
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
            "opciones": forms.CheckboxSelectMultiple,
        }


class HistorialEstadoForm(forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["estado"]
        labels = {"estado": "Estado"}
        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),
        }


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        initial=1,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    tamano = forms.ModelChoiceField(
        label="Tamano",
        required=False,
        queryset=OpcionProducto.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    leche = forms.ModelChoiceField(
        label="Leche",
        required=False,
        queryset=OpcionProducto.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    azucar = forms.ModelChoiceField(
        label="Azucar",
        required=False,
        queryset=OpcionProducto.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto is None:
            opciones = OpcionProducto.objects.none()
        else:
            opciones = OpcionProducto.objects.filter(producto=producto)
        for tipo in ("tamano", "leche", "azucar"):
            self.fields[tipo].queryset = opciones.filter(tipo=tipo)


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Codigo",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Direccion",
        queryset=Direccion.objects.none(),
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
        label="Estado",
        choices=(),
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, estados=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estados is not None:
            self.fields["estado"].choices = estados
