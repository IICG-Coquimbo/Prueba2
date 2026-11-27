from django import forms
from django.contrib.auth.models import User

from apps.cuentas.models import Direccion

from .models import HistorialEstado, ItemPedido, Pedido


class PedidoForm(forms.ModelForm):
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
            "direccion": "Dirección",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
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
            "precio_unitario": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "opciones": forms.CheckboxSelectMultiple,
        }


class HistorialEstadoForm(forms.ModelForm):
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
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Código",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Dirección de entrega",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=Pedido.MetodoPago.choices,
        label="Método de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(
            usuario=usuario
        )


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=[],
        label="Nuevo estado",
        widget=forms.RadioSelect,
    )

    def __init__(self, estados, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = []
        for estado in estados:
            if isinstance(estado, (tuple, list)):
                opciones.append((estado[0], estado[1]))
            else:
                opciones.append((estado, Pedido.Estado(estado).label))
        self.fields["estado"].choices = opciones
