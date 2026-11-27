from django import forms

from apps.cuentas.models import Direccion
from .models import HistorialEstado, ItemPedido, MetodoPago, Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["estado", "direccion", "metodo_pago", "codigo_descuento"]
        labels = {
            "estado": "Estado",
            "direccion": "Direccion",
            "metodo_pago": "Metodo de pago",
            "codigo_descuento": "Codigo de descuento",
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
        labels = {"estado": "Estado", "usuario": "Usuario"}
        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
        }


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Codigo de descuento", max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Direccion de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=MetodoPago.choices,
        widget=forms.RadioSelect
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(
            usuario=usuario
        )


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Estado",
        widget=forms.RadioSelect
    )

    def __init__(self, estados_permitidos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = estados_permitidos
