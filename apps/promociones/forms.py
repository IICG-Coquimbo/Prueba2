from django import forms
from django.core.exceptions import ValidationError
from .models import CodigoDescuento


class CodigoDescuentoForm(forms.ModelForm):
    class Meta:
        model = CodigoDescuento
        fields = ["codigo", "porcentaje", "vigente_desde", "vigente_hasta", "solo_primer_pedido", "activo"]
        labels = {
            "codigo": "Código",
            "porcentaje": "Porcentaje de descuento",
            "vigente_desde": "Vigente desde",
            "vigente_hasta": "Vigente hasta",
            "solo_primer_pedido": "Solo primer pedido",
            "activo": "Activo",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "porcentaje": forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "100"}),
            "vigente_desde": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "vigente_hasta": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "solo_primer_pedido": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_porcentaje(self):
        porcentaje = self.cleaned_data.get("porcentaje")
        if porcentaje is not None and (porcentaje < 1 or porcentaje > 100):
            raise forms.ValidationError("El porcentaje debe estar entre 1 y 100.")
        return porcentaje

    def clean(self):
        cleaned_data = super().clean()
        vigente_desde = cleaned_data.get("vigente_desde")
        vigente_hasta = cleaned_data.get("vigente_hasta")

        if vigente_desde and vigente_hasta and vigente_desde > vigente_hasta:
            self.add_error("vigente_hasta", "La fecha 'vigente hasta' no puede ser anterior a 'vigente desde'.")

        return cleaned_data