from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion
from apps.promociones.models import CodigoDescuento

from .models import Pedido


class _CarritoForm(forms.Form):
    def __init__(self, *args, pedido=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido
        self.usuario = usuario

    def clean(self):
        datos = super().clean()
        if (
            not self.usuario
            or not self.usuario.is_authenticated
            or not self.usuario.has_perm("pedidos.add_pedido")
        ):
            raise ValidationError("No tienes permiso para modificar el carrito.")
        if (
            self.pedido is None
            or self.pedido.pk is None
            or self.pedido.cliente_id != self.usuario.pk
            or self.pedido.estado != Pedido.Estado.CARRITO
        ):
            raise ValidationError("El pedido no es un carrito activo de tu cuenta.")
        return datos


class AgregarAlCarritoForm(_CarritoForm):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        error_messages={"min_value": "La cantidad debe ser al menos 1."},
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        opciones = OpcionProducto.objects.none()
        if producto is not None and producto.pk is not None and producto.disponible:
            opciones = producto.opciones.order_by("nombre", "pk")
        for tipo, etiqueta in OpcionProducto.Tipo.choices:
            self.fields[tipo] = forms.ModelChoiceField(
                label=etiqueta,
                required=False,
                queryset=opciones.filter(tipo=tipo),
                widget=forms.Select(attrs={"class": "form-select"}),
                error_messages={"invalid_choice": "Elige una opción válida de este producto y tipo."},
            )

    def clean(self):
        datos = super().clean()
        if self.producto is None or self.producto.pk is None or not self.producto.disponible:
            raise ValidationError("El producto no está disponible.")
        return datos


class QuitarItemForm(_CarritoForm):
    def __init__(self, *args, item=None, usuario=None, **kwargs):
        super().__init__(
            *args, pedido=item.pedido if item is not None else None, usuario=usuario, **kwargs
        )
        self.item = item

    def clean(self):
        datos = super().clean()
        if self.item is None or self.item.pk is None:
            raise ValidationError("El artículo no pertenece al carrito.")
        return datos


class CodigoForm(_CarritoForm):
    texto = forms.CharField(
        label="Código de descuento",
        max_length=CodigoDescuento._meta.get_field("codigo").max_length,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        datos = super().clean()
        texto = datos.get("texto")
        if texto is None:
            return datos
        codigo = CodigoDescuento.objects.filter(codigo=texto).first()
        hoy = timezone.localdate()
        if codigo is None or not codigo.activo or not (codigo.vigente_desde <= hoy <= codigo.vigente_hasta):
            self.add_error("texto", "El código no existe, está inactivo o no está vigente.")
        elif codigo.solo_primer_pedido and self.usuario.pedidos.exclude(
            estado__in=(Pedido.Estado.CARRITO, Pedido.Estado.PENDIENTE_PAGO)
        ).exists():
            self.add_error("texto", "Este código solo se puede usar en el primer pedido.")
        return datos


class _DireccionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, direccion):
        return f"{direccion.alias} — {direccion.direccion}"


class ConfirmarPedidoForm(_CarritoForm):
    direccion = _DireccionChoiceField(
        label="Dirección de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": "Elige una dirección registrada en tu cuenta."},
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=Pedido.MetodoPago.choices,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        error_messages={"invalid_choice": "Elige efectivo o tarjeta como método de pago."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.usuario and self.usuario.is_authenticated and self.usuario.pk is not None:
            self.fields["direccion"].queryset = self.usuario.direcciones.order_by("alias", "pk")

    def clean(self):
        datos = super().clean()
        if not self.pedido.items.exists():
            raise ValidationError("Agrega al menos un producto antes de confirmar el pedido.")
        return datos


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Siguiente estado",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        error_messages={"invalid_choice": "No puedes cambiar el pedido a ese estado."},
    )

    def __init__(self, *args, pedido=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        siguiente = self._siguiente_estado(pedido, usuario)
        self.fields["estado"].choices = [(siguiente.value, siguiente.label)] if siguiente else []

    @staticmethod
    def _siguiente_estado(pedido, usuario):
        if pedido is None or pedido.pk is None or not usuario or not usuario.is_authenticated:
            return None

        estado = Pedido.Estado
        if pedido.estado == estado.RECIBIDO and usuario.has_perm("pedidos.preparar_pedido"):
            return estado.EN_PREPARACION
        if pedido.estado == estado.EN_PREPARACION and usuario.has_perm("pedidos.preparar_pedido"):
            return estado.LISTO_DESPACHO
        if usuario.has_perm("pedidos.despachar_pedido"):
            if pedido.estado == estado.LISTO_DESPACHO:
                return estado.EN_CAMINO
            if pedido.estado == estado.EN_CAMINO:
                entrega = getattr(pedido, "entrega", None)
                if entrega is not None and entrega.repartidor_id == usuario.pk:
                    return estado.ENTREGADO
        return None

    def clean(self):
        datos = super().clean()
        if not self.fields["estado"].choices:
            raise ValidationError("No puedes avanzar este pedido desde su estado actual.")
        return datos
