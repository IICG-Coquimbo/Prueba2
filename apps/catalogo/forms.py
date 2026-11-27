from django import forms

from .models import Categoria, OpcionProducto, Producto, TipoOpcion


class CategoriaForm(forms.ModelForm):
    """RF-15: administrar categorias."""

    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {"nombre": "Nombre"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProductoForm(forms.ModelForm):
    """RF-15: administrar productos."""

    class Meta:
        model = Producto
        fields = [
            "categoria",
            "nombre",
            "descripcion",
            "precio",
            "imagen_url",
            "disponible",
        ]
        labels = {
            "categoria": "Categoria",
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "precio": "Precio",
            "imagen_url": "Imagen URL",
            "disponible": "Disponible",
        }
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "imagen_url": forms.TextInput(attrs={"class": "form-control"}),
            "disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class OpcionProductoForm(forms.ModelForm):
    """RF-15: administrar opciones de producto."""

    class Meta:
        model = OpcionProducto
        fields = ["producto", "tipo", "nombre", "recargo"]
        labels = {
            "producto": "Producto",
            "tipo": "Tipo",
            "nombre": "Nombre",
            "recargo": "Recargo",
        }
        widgets = {
            "producto": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "recargo": forms.NumberInput(attrs={"class": "form-control"}),
        }


class AgregarAlCarritoForm(forms.Form):
    """RF-04: agregar un producto al carrito, con opciones por tipo."""

    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        for tipo, etiqueta in (
            (TipoOpcion.TAMANO, "Tamano"),
            (TipoOpcion.LECHE, "Leche"),
            (TipoOpcion.AZUCAR, "Azucar"),
        ):
            self.fields[f"opcion_{tipo.value}"] = forms.ModelChoiceField(
                queryset=OpcionProducto.objects.filter(
                    producto=producto, tipo=tipo.value
                ),
                required=False,
                label=etiqueta,
                empty_label="Sin opcion",
                widget=forms.Select(attrs={"class": "form-select"}),
            )

    def opciones_seleccionadas(self):
        """Devuelve las instancias de OpcionProducto elegidas (no vacias)."""
        seleccionadas = []
        for tipo in TipoOpcion:
            opcion = self.cleaned_data.get(f"opcion_{tipo.value}")
            if opcion is not None:
                seleccionadas.append(opcion)
        return seleccionadas
