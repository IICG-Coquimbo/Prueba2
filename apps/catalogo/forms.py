from django import forms

from apps.catalogo.models import OpcionProducto, Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["categoria", "nombre", "descripcion", "precio", "imagen_url", "disponible"]
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
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "imagen_url": forms.URLInput(attrs={"class": "form-control"}),
            "disponible": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is not None and precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor a cero.")
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
            "recargo": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def clean_recargo(self):
        recargo = self.cleaned_data.get("recargo")
        if recargo is not None and recargo < 0:
            raise forms.ValidationError("El recargo no puede ser negativo.")
        return recargo
