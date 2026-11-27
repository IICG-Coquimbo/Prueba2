from django import forms

from .models import OpcionProducto


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Cantidad",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto
        if producto is not None:
            for tipo in OpcionProducto.Tipo.values:
                opciones = producto.opciones.filter(tipo=tipo)
                if opciones.exists():
                    self.fields[f"opcion_{tipo}"] = forms.ModelChoiceField(
                        queryset=opciones,
                        required=False,
                        label=tipo.capitalize(),
                        empty_label="(sin opcion)",
                        widget=forms.Select(attrs={"class": "form-select"}),
                    )

    def opciones_elegidas(self):
        elegidas = []
        for nombre, valor in self.cleaned_data.items():
            if nombre.startswith("opcion_") and valor is not None:
                elegidas.append(valor)
        return elegidas
