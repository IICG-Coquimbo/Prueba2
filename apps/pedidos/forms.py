from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion
from apps.pedidos.models import EstadoPedido, ItemPedido, Pedido
from apps.promociones.models import CodigoDescuento


class PedidoForm(forms.ModelForm):
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        widget=forms.RadioSelect,
        required=False,
    )

    class Meta:
        model = Pedido
        fields = ["metodo_pago", "direccion", "codigo_descuento"]
        labels = {
            "metodo_pago": "Metodo de pago",
            "direccion": "Direccion",
            "codigo_descuento": "Codigo de descuento",
        }
        widgets = {
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()

    def clean(self):
        cleaned = super().clean()
        direccion = cleaned.get("direccion")
        metodo_pago = cleaned.get("metodo_pago")
        if bool(direccion) != bool(metodo_pago):
            raise forms.ValidationError("Debe indicar direccion y metodo de pago juntos.")
        return cleaned


class ItemPedidoForm(forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = ["cantidad", "opciones"]
        labels = {
            "cantidad": "Cantidad",
            "opciones": "Opciones",
        }
        widgets = {
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "opciones": forms.CheckboxSelectMultiple,
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is None or cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        return cantidad


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
    )

    def __init__(self, producto=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if producto is None:
            return
        etiquetas = dict(OpcionProducto.Tipo.choices)
        for tipo in ["tamano", "leche", "azucar"]:
            opciones = producto.opciones.filter(tipo=tipo)
            if not opciones.exists():
                continue
            self.fields["opcion_{}".format(tipo)] = forms.ChoiceField(
                label=etiquetas.get(tipo, tipo),
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
                choices=[("", "Ninguna")] + [(str(opcion.id), opcion.nombre) for opcion in opciones],
            )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Codigo de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_codigo(self):
        return self.cleaned_data.get("codigo", "").strip().upper()


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Direccion",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Metodo de pago",
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario is not None:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Estado",
        widget=forms.RadioSelect,
    )

    def __init__(self, estados=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        etiquetas = dict(EstadoPedido.choices)
        if estados is None:
            estados = []
        self.fields["estado"].choices = [
            (valor, etiquetas.get(valor, valor)) for valor in estados
        ]
