from django import forms
from django.core.exceptions import ValidationError

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion

from .models import HistorialEstado, ItemPedido, Pedido


TIPOS_OPCION = tuple(OpcionProducto.Tipo.values)
PERMISO_PREPARAR = "pedidos.preparar_pedido"
PERMISO_DESPACHAR = "pedidos.despachar_pedido"


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
            "direccion": "Dirección",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
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
        fields = [
            "pedido",
            "producto",
            "cantidad",
            "precio_unitario",
            "opciones",
        ]
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
        fields = [
            "pedido",
            "estado",
            "usuario",
        ]
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
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    tamano = forms.ChoiceField(
        label="Tamaño",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    leche = forms.ChoiceField(
        label="Leche",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    azucar = forms.ChoiceField(
        label="Azúcar",
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        for tipo in TIPOS_OPCION:
            self.fields[tipo].choices = [("", "---------")] + [
                (str(opcion.pk), opcion.nombre)
                for opcion in self._opciones_por_tipo(tipo)
            ]

    def _opciones_por_tipo(self, tipo):
        if self.producto is None:
            return OpcionProducto.objects.none()
        return OpcionProducto.objects.filter(producto=self.producto, tipo=tipo).order_by("nombre")

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is None or cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que 0.")
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        if self.producto is None:
            self.add_error(None, "El producto no está disponible.")
            return cleaned_data

        for tipo in TIPOS_OPCION:
            valor = cleaned_data.get(tipo)
            if not valor:
                continue
            opciones = {str(opcion.pk): opcion for opcion in self._opciones_por_tipo(tipo)}
            if valor not in opciones:
                self.add_error(tipo, "La opción no pertenece al producto.")

        return cleaned_data


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    texto = forms.CharField(
        label="Código",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_texto(self):
        texto = self.cleaned_data.get("texto", "").strip()
        if not texto:
            raise ValidationError("El código es obligatorio.")
        return texto


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        label="Dirección",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=Pedido.MetodoPago.choices,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None and user.is_authenticated:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=user).order_by("alias", "pk")
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        label="Estado",
        choices=[],
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, pedido=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pedido = pedido
        self.user = user
        self.fields["estado"].choices = [
            (estado, dict(Pedido.Estado.choices).get(estado, estado))
            for estado in self._estados_permitidos()
        ]

    def _estados_permitidos(self):
        if self.pedido is None or self.user is None or not self.user.is_authenticated:
            return []

        estados = []
        estado_actual = self.pedido.estado

        if self.user.has_perm(PERMISO_PREPARAR):
            if estado_actual == Pedido.Estado.RECIBIDO:
                estados.append(Pedido.Estado.EN_PREPARACION)
            elif estado_actual == Pedido.Estado.EN_PREPARACION:
                estados.append(Pedido.Estado.LISTO_DESPACHO)

        if self.user.has_perm(PERMISO_DESPACHAR):
            if estado_actual == Pedido.Estado.LISTO_DESPACHO:
                estados.append(Pedido.Estado.EN_CAMINO)
            elif estado_actual == Pedido.Estado.EN_CAMINO and self._es_repartidor_de_entrega():
                estados.append(Pedido.Estado.ENTREGADO)

        return estados

    def _es_repartidor_de_entrega(self):
        entrega = getattr(self.pedido, "entrega", None)
        return entrega is not None and entrega.repartidor_id == self.user.id

    def clean_estado(self):
        estado = self.cleaned_data.get("estado")
        if estado not in [valor for valor, _etiqueta in self.fields["estado"].choices]:
            raise ValidationError("Estado no permitido.")
        return estado
