"""Formularios de la app pedidos segun docs/reglas_formularios.md y docs/reglas_flujo.md."""

from django import forms

from .models import HistorialEstado, ItemPedido, Pedido


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
            "opciones": forms.CheckboxSelectMultiple,
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
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if producto:
            for tipo in ("tamano", "leche", "azucar"):
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        label=opciones.first().get_tipo_display(),
                        queryset=opciones,
                        required=False,
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
        label="Direccion de entrega",
        queryset=None,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=[
            ("efectivo", "Efectivo contra entrega"),
            ("tarjeta", "Tarjeta en linea"),
        ],
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario=None, *args, **kwargs):
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

    def __init__(self, estados_permitidos=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if estados_permitidos is not None:
            self.fields["estado"].choices = estados_permitidos
