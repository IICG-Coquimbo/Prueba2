from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion

from .models import HistorialEstado, ItemPedido, Pedido


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto is None:
            return
        for tipo in OpcionProducto.Tipo:
            queryset = producto.opciones.filter(tipo=tipo.value)
            if queryset.exists():
                self.fields[f"opcion_{tipo.value}"] = forms.ModelChoiceField(
                    queryset=queryset,
                    required=False,
                    label=tipo.label,
                    empty_label=f"Sin {tipo.label.lower()}",
                    widget=forms.Select(attrs={"class": "form-select"}),
                )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    texto = forms.CharField(
        label="Codigo de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Direccion",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=Pedido.MetodoPago.choices,
        label="Metodo de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(choices=[], label="Nuevo estado", widget=forms.RadioSelect)

    def __init__(self, *args, opciones=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = opciones or []


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
