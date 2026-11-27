from django import forms
from apps.pedidos.models import Pedido
from apps.cuentas.models import Direccion
from apps.promociones.models import CodigoDescuento


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Codigo de descuento",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. BIENVENIDA10"})
    )

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        try:
            descuento = CodigoDescuento.objects.get(codigo__iexact=codigo)
        except CodigoDescuento.DoesNotExist:
            raise forms.ValidationError("Codigo no existe.")
        if not descuento.activo:
            raise forms.ValidationError("Codigo no esta activo.")
        from django.utils import timezone
        hoy = timezone.now().date()
        if not (descuento.vigente_desde <= hoy <= descuento.vigente_hasta):
            raise forms.ValidationError("Codigo fuera de vigencia.")
        return codigo


class ConfirmarPedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["direccion", "metodo_pago"]
        labels = {
            "direccion": "Direccion de entrega",
            "metodo_pago": "Metodo de pago",
        }
        widgets = {
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)
        self.fields["direccion"].empty_label = "Seleccione una direccion"
        self.fields["metodo_pago"].choices = Pedido.MetodoPago.choices

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("direccion"):
            self.add_error("direccion", "Debe seleccionar una direccion.")
        if not cleaned_data.get("metodo_pago"):
            self.add_error("metodo_pago", "Debe seleccionar un metodo de pago.")
        return cleaned_data


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"})
    )

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        if pedido:
            from apps.pedidos.servicios import TRANSICIONES
            permitidos = TRANSICIONES.get(pedido.estado, [])
            self.fields["estado"].choices = [
                (e, Pedido.Estado(e).label) for e in permitidos
            ]