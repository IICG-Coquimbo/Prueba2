from django import forms
from django.contrib.auth.models import User
from .models import Pedido, ItemPedido, HistorialEstado


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["cliente", "estado", "direccion", "metodo_pago", "codigo_descuento", "subtotal", "descuento", "total", "creado"]
        labels = {
            "cliente": "Cliente",
            "estado": "Estado",
            "direccion": "Dirección",
            "metodo_pago": "Método de pago",
            "codigo_descuento": "Código de descuento",
            "subtotal": "Subtotal",
            "descuento": "Descuento",
            "total": "Total",
            "creado": "Creado",
        }
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "direccion": forms.Select(attrs={"class": "form-select"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
            "codigo_descuento": forms.Select(attrs={"class": "form-select"}),
            "subtotal": forms.NumberInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "descuento": forms.NumberInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "total": forms.NumberInput(attrs={"class": "form-control", "readonly": "readonly"}),
            "creado": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date", "readonly": "readonly"}),
        }


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
            "cantidad": forms.NumberInput(attrs={"class": "form-control"}),
            "precio_unitario": forms.NumberInput(attrs={"class": "form-control"}),
            "opciones": forms.CheckboxSelectMultiple,
        }


class HistorialEstadoForm(forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["pedido", "estado", "fecha", "usuario"]
        labels = {
            "pedido": "Pedido",
            "estado": "Estado",
            "fecha": "Fecha",
            "usuario": "Usuario",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
        }


# Formularios de acción (Action Forms)

class AgregarAlCarritoForm(forms.Form):
    """Formulario para agregar un item al carrito."""
    cantidad = forms.PositiveIntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    producto = forms.ModelChoiceField(
        label="Producto",
        queryset=None,  # Se filtrará en __init__
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )

    def __init__(self, *args, producto_queryset=None, **kwargs):
        super().__init(*args, **kwargs)
        if producto_queryset is not None:
            self.fields["producto"].queryset = producto_queryset
        # Agregar selects de opciones opcionales
        for tipo in ["tamano", "leche", "azucar"]:
            self.fields[f"opcion_{tipo}"] = forms.ChoiceField(
                label=f"Opción {tipo}",
                required=False,
                widget=forms.Select(attrs={"class": "form-select"}),
            )


class QuitarItemForm(forms.Form):
    """Formulario para quitar un item del carrito (sin campos)."""
    pass


class CodigoForm(forms.Form):
    """Formulario para ingresar un código de descuento en el carrito."""
    codigo = forms.CharField(
        label="Código de descuento",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    """Formulario para confirmar un pedido (dirección y método de pago)."""
    direccion = forms.ModelChoiceField(
        label="Dirección",
        queryset=None,  # Se filtrará en __init__ con las direcciones del usuario
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    metodo_pago = forms.ChoiceField(
        label="Método de pago",
        choices=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        widget=forms.RadioSelect,
    )


class PasarelaForm(forms.Form):
    """Formulario de la pasarela de pago simulada."""
    resultado = forms.ChoiceField(
        label="Resultado del pago",
        choices=[("exitoso", "Pago exitoso"), ("fallido", "Pago fallido")],
        widget=forms.RadioSelect,
    )


class EstadoPedidoForm(forms.Form):
    """Formulario para cambiar el estado del pedido."""
    estado = forms.ChoiceField(
        label="Estado",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init(*args, **kwargs)
        # Filtrar estados permitidos según el rol del usuario
        estados_permitidos = ["recibido", "en_preparacion", "listo_despacho", "en_camino", "entregado"]
        if usuario and hasattr(usuario, "is_staff") and usuario.is_staff:
            # Admin puede ver más estados
            pass
        else:
            # Cliente solo puede ver estados avanzados
            self.fields["estado"].choices = [
                ("recibido", "Recibido"),
                ("en_preparacion", "En preparación"),
                ("listo_despacho", "Listo para despacho"),
            ]