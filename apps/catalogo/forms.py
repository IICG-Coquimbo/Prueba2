from django import forms
from django.core.validators import MinValueValidator

from .models import Categoria, Producto, OpcionProducto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {
            "nombre": "Nombre",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre")
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["categoria", "nombre", "descripcion", "precio", "imagen_url", "disponible"]
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
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "precio": forms.NumberInput(attrs={"class": "form-control"}),
            "imagen_url": forms.TextInput(attrs={"class": "form-control"}),
            "disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio


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

    def clean_recargo(self):
        recargo = self.cleaned_data.get("recargo")
        if recargo is not None and recargo < 0:
            raise forms.ValidationError("El recargo no puede ser negativo.")
        return recargo


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, producto=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if producto:
            for tipo in ["tamano", "leche", "azucar"]:
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        label=f"{tipo.capitalize()}",
                        queryset=opciones,
                        required=False,
                        widget=forms.Select(attrs={"class": "form-select"}),
                        empty_label="Sin seleccionar",
                    )

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is not None and cantidad < 1:
            raise forms.ValidationError("La cantidad debe ser mayor que cero.")
        return cantidad
