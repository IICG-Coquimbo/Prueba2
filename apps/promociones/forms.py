from django import forms

from .models import CodigoDescuento


class CodigoDescuentoForm(forms.ModelForm):
    class Meta:
        model = CodigoDescuento
        fields = [
            "codigo",
            "porcentaje",
            "vigente_desde",
            "vigente_hasta",
            "solo_primer_pedido",
            "activo",
        ]
        labels = {
            "codigo": "Código",
            "porcentaje": "Porcentaje",
            "vigente_desde": "Vigente desde",
            "vigente_hasta": "Vigente hasta",
            "solo_primer_pedido": "Solo primer pedido",
            "activo": "Activo",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "porcentaje": forms.NumberInput(attrs={"class": "form-control"}),
            "vigente_desde": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "vigente_hasta": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "solo_primer_pedido": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
