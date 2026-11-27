from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Pedido, ItemPedido
from apps.cuentas.models import Direccion
from apps.catalogo.models import Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["direccion", "metodo_pago", "codigo_descuento"]
        labels = {
            "direccion": "Dirección de entrega",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
        }
        widgets = {
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=user)
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()

        # Filtrar códigos de descuento activos y vigentes
        from django.utils import timezone
        hoy = timezone.now().date()
        self.fields["codigo_descuento"].queryset = CodigoDescuento.objects.filter(
            activo=True,
            vigente_desde__lte=hoy,
            vigente_hasta__gte=hoy,
        )


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
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "opciones": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo productos disponibles
        self.fields["producto"].queryset = Producto.objects.filter(disponible=True)
        # Solo opciones del producto seleccionado (se filtra en la vista con JS o se deja vacío)
        self.fields["opciones"].queryset = OpcionProducto.objects.none()

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
        return cantidad


class AgregarAlCarritoForm(forms.Form):
    producto_id = forms.IntegerField(widget=forms.HiddenInput())
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label="Cantidad",
    )
    opciones_ids = forms.ModelMultipleChoiceField(
        queryset=OpcionProducto.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Opciones",
    )

    def __init__(self, *args, **kwargs):
        producto = kwargs.pop("producto", None)
        super().__init__(*args, **kwargs)

        if producto:
            self.fields["opciones_ids"].queryset = producto.opciones.all()

    def clean(self):
        cleaned_data = super().clean()
        producto_id = cleaned_data.get("producto_id")
        opciones_ids = cleaned_data.get("opciones_ids")

        if producto_id:
            try:
                producto = Producto.objects.get(pk=producto_id)
            except Producto.DoesNotExist:
                raise ValidationError("El producto no existe.")

            if not producto.disponible:
                raise ValidationError("El producto no está disponible.")

            # Validar que las opciones pertenezcan al producto
            if opciones_ids:
                for opcion in opciones_ids:
                    if opcion.producto_id != producto_id:
                        self.add_error("opciones_ids", f"La opción '{opcion.nombre}' no pertenece a este producto.")

        return cleaned_data


class ActualizarCarritoForm(forms.Form):
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    cantidad = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label="Cantidad",
    )

    def clean(self):
        cleaned_data = super().clean()
        item_id = cleaned_data.get("item_id")

        if item_id:
            try:
                item = ItemPedido.objects.select_related("pedido").get(pk=item_id)
            except ItemPedido.DoesNotExist:
                raise ValidationError("El item no existe.")

            # Solo se puede actualizar si el pedido está en estado carrito
            if item.pedido.estado != Pedido.Estado.CARRITO:
                raise ValidationError("Solo se puede modificar el carrito mientras está en estado 'carrito'.")

        return cleaned_data


class AplicarDescuentoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Código de descuento"}),
        label="Código de descuento",
    )

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo", "").strip().upper()

        if not codigo:
            raise forms.ValidationError("Ingrese un código de descuento.")

        try:
            descuento = CodigoDescuento.objects.get(codigo__iexact=codigo)
        except CodigoDescuento.DoesNotExist:
            raise forms.ValidationError("El código de descuento no existe.")

        from django.utils import timezone
        hoy = timezone.now().date()

        if not descuento.activo:
            raise forms.ValidationError("El código de descuento no está activo.")

        if descuento.vigente_desde > hoy:
            raise forms.ValidationError("El código de descuento aún no es válido.")

        if descuento.vigente_hasta < hoy:
            raise forms.ValidationError("El código de descuento ha expirado.")

        return codigo


class ConfirmarPedidoForm(forms.Form):
    """
    Formulario para confirmar el pedido (carrito -> pendiente_pago/recibido).
    direccion: Select con las direcciones del usuario.
    metodo_pago: RadioSelect con las opciones del modelo.
    """
    direccion = forms.ModelChoiceField(
        queryset=Direccion.objects.none(),
        label="Dirección de entrega",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Seleccione una dirección",
    )
    metodo_pago = forms.ChoiceField(
        choices=Pedido.MetodoPago.choices,
        label="Método de pago",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=user)
        else:
            self.fields["direccion"].queryset = Direccion.objects.none()

    def clean_direccion(self):
        direccion = self.cleaned_data.get("direccion")
        if not direccion:
            raise forms.ValidationError("Debe seleccionar una dirección de entrega.")
        return direccion


class QuitarItemForm(forms.Form):
    """
    Formulario vacío para quitar un item del carrito.
    El item_id se pasa por URL.
    """
    pass


class EstadoPedidoForm(forms.Form):
    """
    Formulario para avanzar el estado del pedido.
    estado: RadioSelect con el siguiente estado permitido para el rol.
    El nuevo_estado se pasa por __init__ según el rol y estado actual.
    """
    estado = forms.ChoiceField(
        choices=[],
        label="Nuevo estado",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        estados_permitidos = kwargs.pop("estados_permitidos", [])
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = estados_permitidos