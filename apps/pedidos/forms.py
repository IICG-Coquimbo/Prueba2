from django import forms

from apps.cuentas.models import Direccion


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for tipo, etiqueta in (
            ("tamano", "Tamaño"),
            ("leche", "Leche"),
            ("azucar", "Azúcar"),
        ):
            self.fields[f"opcion_{tipo}"] = forms.ChoiceField(
                choices=[
                    (opcion.id, opcion.nombre)
                    for opcion in producto.opciones.filter(tipo=tipo)
                ],
                required=False,
                label=etiqueta,
                widget=forms.Select(attrs={"class": "form-select"}),
            )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Código de descuento",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Dirección",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        label="Método de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    def __init__(self, estados, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"] = forms.ChoiceField(
            choices=estados,
            label="Estado",
            widget=forms.RadioSelect,
        )
