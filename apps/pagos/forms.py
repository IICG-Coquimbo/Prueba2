from django import forms
from django.core.exceptions import ValidationError

from apps.pedidos.models import Pedido

from .models import Pago


class PasarelaForm(forms.Form):
    resultado = forms.TypedChoiceField(
        label="Resultado del pago",
        choices=[(Pago.Estado.EXITOSO, "Pago exitoso"), (Pago.Estado.FALLIDO, "Pago fallido")],
        coerce=lambda valor: valor == Pago.Estado.EXITOSO,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        error_messages={"invalid_choice": "Selecciona Pago exitoso o Pago fallido."},
    )

    def __init__(self, *args, pago=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pago = pago
        self.usuario = usuario

    def clean(self):
        datos = super().clean()
        pago = self.pago
        usuario = self.usuario
        if (
            pago is None
            or pago.pk is None
            or not usuario
            or not usuario.is_authenticated
            or not usuario.has_perm("pedidos.add_pedido")
            or pago.pedido.cliente_id != usuario.pk
        ):
            raise ValidationError("No tienes acceso a este pago.")
        if (
            pago.metodo != Pedido.MetodoPago.TARJETA
            or pago.estado != Pago.Estado.PENDIENTE
            or pago.pedido.estado != Pedido.Estado.PENDIENTE_PAGO
        ):
            raise ValidationError("El pedido no tiene un pago con tarjeta pendiente de resolución.")
        return datos
