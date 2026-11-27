from django import forms
from django.contrib.auth.models import User

from .models import Pedido, ItemPedido, HistorialEstado
from apps.cuentas.models import Direccion
from apps.promociones.models import CodigoDescuento


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["direccion", "metodo_pago", "codigo_descuento"]
        labels = {
            "direccion": "Dirección",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
        }
        widgets = {
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)
            self.fields["codigo_descuento"].queryset = CodigoDescuento.objects.filter(activo=True)


class ItemPedidoForm(forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = ["cantidad", "opciones"]
        labels = {
            "cantidad": "Cantidad",
            "opciones": "Opciones",
        }
        widgets = {
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "opciones": forms.CheckboxSelectMultiple,
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad


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


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo")
        if not codigo:
            raise forms.ValidationError("El código es obligatorio.")
        return codigo


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Dirección de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=[
            ("efectivo", "Efectivo"),
            ("tarjeta", "Tarjeta"),
        ],
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=[],
        widget=forms.RadioSelect,
    )

    def __init__(self, estado_siguiente=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if estado_siguiente:
            self.fields["estado"].choices = [(estado_siguiente, estado_siguiente.replace("_", " ").capitalize())]


class PasarelaForm(forms.Form):
    resultado = forms.ChoiceField(
        label="Resultado del pago",
        choices=[
            ("exitoso", "Pago exitoso"),
            ("fallido", "Pago fallido"),
        ],
        widget=forms.RadioSelect,
    )
