from django import forms

from .models import Categoria, OpcionProducto, Producto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {"nombre": "Nombre"}
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"})
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "categoria", "nombre", "descripcion", "precio",
            "imagen_url", "disponible",
        ]
        labels = {
            "categoria": "Categoria",
            "nombre": "Nombre",
            "descripcion": "Descripcion",
            "precio": "Precio",
            "imagen_url": "URL de la imagen",
            "disponible": "Disponible",
        }
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "imagen_url": forms.URLInput(attrs={"class": "form-control"}),
            "disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
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
        label="Cantidad", min_value=1, initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    def __init__(self, producto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for tipo in ["tamano", "leche", "azucar"]:
            opciones = producto.opciones.filter(tipo=tipo)
            if opciones.exists():
                self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                    label=tipo.title(),
                    queryset=opciones,
                    required=False,
                    widget=forms.Select(attrs={"class": "form-select"}),
                )
