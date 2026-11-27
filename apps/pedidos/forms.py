from django import forms

from apps.catalogo.models import OpcionProducto
from apps.cuentas.models import Direccion
from apps.pedidos.servicios import TRANSICIONES

from .models import EstadoPedido, HistorialEstado, ItemPedido, MetodoPago, Pedido


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
            "subtotal": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "descuento": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "total": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        for campo in ("subtotal", "descuento", "total"):
            valor = cleaned_data.get(campo)
            if valor is not None and valor < 0:
                self.add_error(campo, "El monto no puede ser negativo.")
        subtotal = cleaned_data.get("subtotal")
        descuento = cleaned_data.get("descuento")
        if subtotal is not None and descuento is not None and descuento > subtotal:
            self.add_error("descuento", "El descuento no puede superar el subtotal.")
        return cleaned_data


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
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "precio_unitario": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "opciones": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        producto = producto or getattr(getattr(self, "instance", None), "producto", None)
        if producto is not None and getattr(producto, "pk", None):
            self.fields["opciones"].queryset = OpcionProducto.objects.filter(
                producto=producto
            )

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad

    def clean_precio_unitario(self):
        precio = self.cleaned_data["precio_unitario"]
        if precio < 0:
            raise forms.ValidationError("El precio unitario no puede ser negativo.")
        return precio

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get("producto")
        tipos = set()
        for opcion in cleaned_data.get("opciones") or []:
            if producto is not None and opcion.producto_id != producto.pk:
                self.add_error(
                    "opciones", "Cada opción debe pertenecer al producto elegido."
                )
            if opcion.tipo in tipos:
                self.add_error(
                    "opciones",
                    "Solo se permite una opción por tipo (tamaño, leche o azúcar).",
                )
            tipos.add(opcion.tipo)
        return cleaned_data


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
    """Cantidad y, como máximo, una opción de cada tipo del producto."""

    TIPOS_OPCION = [
        (OpcionProducto.TipoOpcion.TAMANO, "Tamaño"),
        (OpcionProducto.TipoOpcion.LECHE, "Leche"),
        (OpcionProducto.TipoOpcion.AZUCAR, "Azúcar"),
    ]

    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        error_messages={
            "required": "Ingrese la cantidad.",
            "invalid": "Ingrese un número entero.",
        },
    )
    opcion_tamano = forms.ModelChoiceField(
        label="Tamaño",
        queryset=OpcionProducto.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    opcion_leche = forms.ModelChoiceField(
        label="Leche",
        queryset=OpcionProducto.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    opcion_azucar = forms.ModelChoiceField(
        label="Azúcar",
        queryset=OpcionProducto.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, producto=None, *args, **kwargs):
        self.producto = producto
        super().__init__(*args, **kwargs)
        for tipo, _etiqueta in self.TIPOS_OPCION:
            campo = "opcion_{}".format(tipo)
            if self.producto is not None and getattr(self.producto, "pk", None):
                self.fields[campo].queryset = OpcionProducto.objects.filter(
                    producto=self.producto, tipo=tipo
                )
            else:
                self.fields[campo].queryset = OpcionProducto.objects.none()

    def clean_cantidad(self):
        cantidad = self.cleaned_data["cantidad"]
        if cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        if self.producto is not None and not self.producto.disponible:
            raise forms.ValidationError("El producto no está disponible.")
        opciones = []
        for tipo, _etiqueta in self.TIPOS_OPCION:
            campo = "opcion_{}".format(tipo)
            cleaned_data[tipo] = cleaned_data.get(campo)
            opcion = cleaned_data[campo]
            if opcion is None:
                continue
            if self.producto is not None and opcion.producto_id != self.producto.pk:
                self.add_error(campo, "La opción no pertenece al producto elegido.")
                continue
            if getattr(opcion, "tipo", None) != tipo:
                self.add_error(campo, "La opción no corresponde a este tipo.")
                continue
            opciones.append(opcion)
        cleaned_data["opciones"] = opciones
        return cleaned_data


class QuitarItemForm(forms.Form):
    """Acción sin campos: el item se identifica en la URL."""


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        label="Código de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        error_messages={"required": "Ingrese un código de descuento."},
    )

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().upper()
        if not codigo:
            raise forms.ValidationError("Ingrese un código de descuento.")
        return codigo


class ConfirmarPedidoForm(forms.Form):
    """Dirección del cliente y método de pago para confirmar el carrito."""

    direccion = forms.ModelChoiceField(
        label="Dirección de entrega",
        queryset=Direccion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"required": "Seleccione una dirección de entrega."},
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=MetodoPago.choices,
        widget=forms.RadioSelect,
        error_messages={"required": "Seleccione un método de pago."},
    )

    def __init__(self, usuario=None, *args, **kwargs):
        pedido = kwargs.pop("pedido", None)
        if pedido is not None and usuario is None:
            usuario = getattr(pedido, "cliente", None)
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        if usuario is not None and getattr(usuario, "pk", None):
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        direccion = cleaned_data.get("direccion")
        if (
            direccion is not None
            and self.usuario is not None
            and direccion.usuario_id != self.usuario.pk
        ):
            self.add_error("direccion", "Seleccione una dirección propia.")
        return cleaned_data


class EstadoPedidoForm(forms.Form):
    """RadioSelect con el siguiente estado permitido según el rol del usuario."""

    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=(),
        widget=forms.RadioSelect,
        error_messages={"required": "Seleccione el nuevo estado."},
    )

    def __init__(
        self, *args, pedido=None, usuario=None, estados_permitidos=None, **kwargs
    ):
        if args and isinstance(args[0], Pedido):
            pedido = args[0]
            args = args[1:]
        self.pedido = pedido
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        self.estados_permitidos = self._estados_permitidos(estados_permitidos)
        etiquetas = dict(EstadoPedido.choices)
        self.fields["estado"].choices = [
            (estado, etiquetas.get(estado, estado)) for estado in self.estados_permitidos
        ]

    def _estados_permitidos(self, estados_permitidos):
        if estados_permitidos is not None:
            return [str(getattr(estado, "value", estado)) for estado in estados_permitidos]
        if self.pedido is None:
            return []
        posibles = TRANSICIONES.get(self.pedido.estado, [])
        if isinstance(posibles, str):
            posibles = [posibles]
        if self.usuario is not None and not getattr(self.usuario, "is_superuser", False):
            puede_preparar = self.usuario.has_perm("pedidos.preparar_pedido")
            puede_despachar = self.usuario.has_perm("pedidos.despachar_pedido")
            preparacion = {
                str(EstadoPedido.EN_PREPARACION),
                str(EstadoPedido.LISTO_DESPACHO),
            }
            despacho = {str(EstadoPedido.EN_CAMINO), str(EstadoPedido.ENTREGADO)}
            posibles = [
                estado
                for estado in posibles
                if (
                    str(getattr(estado, "value", estado)) in preparacion
                    and puede_preparar
                )
                or (
                    str(getattr(estado, "value", estado)) in despacho
                    and puede_despachar
                )
            ]
        return [str(getattr(estado, "value", estado)) for estado in posibles]

    def clean_estado(self):
        estado = self.cleaned_data["estado"]
        if estado not in self.estados_permitidos:
            raise forms.ValidationError("Este cambio de estado no está permitido.")
        return estado
