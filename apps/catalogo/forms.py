from django import forms
from apps.catalogo.models import OpcionProducto


class AgregarAlCarritoForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1})
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        if producto:
            opciones = producto.opciones.all()
            for tipo in OpcionProducto.TipoOpcion.values:
                qs = opciones.filter(tipo=tipo)
                if qs.exists():
                    choices = [("", f"--- {tipo.capitalize()} ---")] + [
                        (o.pk, f"{o.nombre} {'(+$' + str(o.recargo) + ')' if o.recargo else ''}")
                        for o in qs
                    ]
                    self.fields[f"opcion_{tipo}"] = forms.ChoiceField(
                        choices=choices,
                        required=False,
                        label=tipo.capitalize(),
                        widget=forms.Select(attrs={"class": "form-select"})
                    )