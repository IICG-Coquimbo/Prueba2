from django import forms

from apps.catalogo.models import TipoOpcion
from apps.cuentas.models import Direccion

from .models import EstadoPedido, HistorialEstado, ItemPedido, MetodoPago, Pedido


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            "direccion",
            "metodo_pago",
            "codigo_descuento",
            "subtotal",
            "descuento",
            "total",
        ]
        labels = {
            "direccion": "Direccion",
            "metodo_pago": "Metodo de pago",
            "codigo_descuento": "Codigo de descuento",
            "subtotal": "Subtotal",
            "descuento": "Descuento",
            "total": "Total",
        }
        widgets = {
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
            "opciones": forms.CheckboxSelectMultiple(),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que 0.")
        return cantidad


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


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        for tipo in TipoOpcion.values:
            self.fields[tipo] = forms.ModelChoiceField(
                queryset=producto.opciones.filter(tipo=tipo),
                label=TipoOpcion(tipo).label,
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
            )

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor que 0.")
        return cantidad


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Codigo",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Direccion",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=MetodoPago.choices,
        label="Metodo de pago",
        widget=forms.RadioSelect(),
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=[],
        label="Estado",
        widget=forms.RadioSelect(),
    )

    def __init__(self, estados, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opciones = []
        for estado in estados:
            if isinstance(estado, (tuple, list)):
                opciones.append(tuple(estado))
            else:
                opciones.append(
                    (estado, dict(EstadoPedido.choices).get(estado, str(estado)))
                )
        self.fields["estado"].choices = opciones
