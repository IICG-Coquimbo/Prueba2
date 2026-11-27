from django import forms
from .models import Pedido, ItemPedido, HistorialEstado


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["cliente", "estado", "direccion", "metodo_pago", "codigo_descuento", "subtotal", "descuento", "total"]
        labels = {
            "cliente": "Cliente",
            "estado": "Estado",
            "direccion": "Direccion",
            "metodo_pago": "Metodo de pago",
            "codigo_descuento": "Codigo de descuento",
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
            "opciones": forms.CheckboxSelectMultiple(),
        }


class HistorialEstadoForm(forms.ModelForm):
    class Meta:
        model = HistorialEstado
        fields = ["pedido", "estado", "usuario"]
        labels = {
            "pedido": "Pedido",
            "estado": "Estado",
            "fecha": "Fecha",
            "usuario": "Usuario",
        }
        widgets = {
            "pedido": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateTimeInput(attrs={"class": "form-control"}),
            "usuario": forms.Select(attrs={"class": "form-select"}),
        }


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto:
            for tipo in ["tamano", "leche", "azucar"]:
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        queryset=opciones,
                        required=False,
                        label=tipo.capitalize(),
                        widget=forms.Select(attrs={"class": "form-select"}),
                    )


class QuitarItemForm(forms.Form):
    pass


class CodigoForm(forms.Form):
    codigo = forms.CharField(
        max_length=20,
        label="Codigo de descuento",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ConfirmarPedidoForm(forms.Form):
    direccion = forms.ModelChoiceField(
        queryset=None,
        label="Direccion de entrega",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    metodo_pago = forms.ChoiceField(
        choices=[("efectivo", "Efectivo contra entrega"), ("tarjeta", "Tarjeta en linea")],
        label="Metodo de pago",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario:
            from apps.cuentas.models import Direccion
            self.fields["direccion"].queryset = Direccion.objects.filter(usuario=usuario)


class EstadoPedidoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=[],
        label="Nuevo estado",
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, pedido=None, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pedidos.servicios import TRANSICIONES
        siguientes = TRANSICIONES.get(pedido.estado, [])
        if not isinstance(siguientes, list):
            siguientes = [siguientes]
        es_barista = usuario.has_perm("pedidos.preparar_pedido") if usuario else False
        es_despachador = usuario.has_perm("pedidos.despachar_pedido") if usuario else False
        validos = []
        for s in siguientes:
            if s in ["en_preparacion", "listo_despacho"] and es_barista:
                validos.append(s)
            elif s in ["en_camino", "entregado"] and es_despachador:
                validos.append(s)
        if validos:
            self.fields["estado"].choices = [(s, s.replace("_", " ").title()) for s in validos]
