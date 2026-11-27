from django import forms
from django.db.models import Q

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        self.campos_opciones = []
        if not producto:
            return
        for tipo, etiqueta in OpcionProducto.Tipo.choices:
            opciones = OpcionProducto.objects.filter(producto=producto, tipo=tipo).order_by("id")
            if not opciones.exists():
                continue
            nombre_campo = f"opcion_{tipo}"
            self.fields[nombre_campo] = forms.ModelChoiceField(
                label=etiqueta,
                queryset=opciones,
                required=False,
                empty_label="Sin selección",
                widget=forms.Select(attrs={"class": "form-select"}),
            )
            self.campos_opciones.append(nombre_campo)

    def get_opciones(self):
        opciones = []
        for nombre_campo in self.campos_opciones:
            opcion = self.cleaned_data.get(nombre_campo)
            if opcion:
                opciones.append(opcion)
        return opciones


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ingresa tu código"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Dirección de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Forma de pago",
        choices=[("efectivo", "Efectivo contra entrega"), ("tarjeta", "Tarjeta en línea")],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario).order_by("alias")


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(label="Nuevo estado", widget=forms.RadioSelect, choices=[])

    def __init__(self, *args, estados=None, **kwargs):
        super().__init__(*args, **kwargs)
        estados = estados or []
        self.fields["estado"].choices = estados
