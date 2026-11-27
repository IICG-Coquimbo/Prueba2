from django import forms

from .models import Categoria, OpcionProducto, Producto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {"nombre": "Nombre"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProductoForm(forms.ModelForm):
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
            "categoria": "Categoría",
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "precio": "Precio",
            "imagen_url": "URL de la imagen",
            "disponible": "Disponible",
        }
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "imagen_url": forms.TextInput(attrs={"class": "form-control"}),
            "disponible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class OpcionProductoForm(forms.ModelForm):
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
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        etiquetas = {
            "tamano": "Tamaño",
            "leche": "Leche",
            "azucar": "Azúcar",
        }
        for tipo in OpcionProducto.TipoOpcion.values:
            self.fields[tipo] = forms.ModelChoiceField(
                queryset=OpcionProducto.objects.filter(
                    producto=producto, tipo=tipo
                ),
                required=False,
                empty_label="Sin opción",
                label=etiquetas[tipo],
                widget=forms.Select(attrs={"class": "form-select"}),
            )
