from django import forms
from django.contrib.auth.models import User

from apps.catalogo.models import OpcionProducto, Producto
from apps.cuentas.models import Direccion
from apps.promociones.models import CodigoDescuento

from .models import EstadoPedido, HistorialEstado, ItemPedido, MetodoPago, Pedido


class PedidoForm(forms.ModelForm):
    """RF-07: alta y edicion de pedidos."""

    class Meta:
        model = Pedido
        fields = [
            "cliente",
            "estado",
            "direccion",
            "metodo_pago",
            "codigo_descuento",
            "subtotal",
            "descuento",
            "total",
        ]
        labels = {
            "cliente": "Cliente",
            "estado": "Estado",
            "direccion": "Direccion",
            "metodo_pago": "Metodo de pago",
            "codigo_descuento": "Codigo de descuento",
            "subtotal": "Subtotal",
            "descuento": "Descuento",
            "total": "Total",
        }
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
            "subtotal": forms.NumberInput(attrs={"class": "form-control"}),
            "descuento": forms.NumberInput(attrs={"class": "form-control"}),
            "total": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ItemPedidoForm(forms.ModelForm):
    """RF-04: items del carrito, con opciones multiples."""

    class Meta:
        model = ItemPedido
        fields = ["pedido", "producto", "cantidad", "precio_unitario", "opciones"]
        labels = {
            "pedido": "Pedido",
            "producto": "Producto",
            "cantidad": "Cantidad",
            "precio_unitario": "Precio unitario",
            "opciones": "Opciones",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "producto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control"}),
            "opciones": forms.CheckboxSelectMultiple(),
        }


class HistorialEstadoForm(forms.ModelForm):
    """RNF-07: registrar cambios de estado."""

    class Meta:
        model = HistorialEstado
        fields = ["pedido", "estado", "usuario"]
        labels = {
            "pedido": "Pedido",
            "estado": "Estado",
            "usuario": "Usuario",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
        }


class QuitarItemForm(forms.Form):
    """RF-04: quitar item del carrito"""


class CodigoForm(forms.Form):
    """RF-16: aplicar un codigo de descuento al carrito."""

    codigo = forms.CharField(
        max_length=20,
        label="Codigo",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    """RF-07: confirmar el carrito con direccion y metodo de pago propios."""

    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Direccion",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=MetodoPago.choices,
        label="Metodo de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    """RF-12/RF-14: avanzar al siguiente estado permitido para el rol."""

    estado = forms.ChoiceField(label="Estado", widget=forms.RadioSelect)

    def __init__(self, estados, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = estados
