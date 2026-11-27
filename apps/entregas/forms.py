from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Entrega
from apps.pedidos.models import Pedido


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ["repartidor", "inicio", "fin"]
        labels = {
            "repartidor": "Repartidor",
            "inicio": "Inicio de entrega",
            "fin": "Fin de entrega",
        }
        widgets = {
            "repartidor": forms.Select(attrs={"class": "form-select"}),
            "inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "fin": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar usuarios que pueden ser repartidores (con permiso o grupo)
        self.fields["repartidor"].queryset = User.objects.filter(
            is_active=True
        ).order_by("username")

        # Si la entrega ya existe (tiene pk), inicio es de solo lectura
        if self.instance.pk:
            self.fields["inicio"].widget.attrs["readonly"] = True

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("inicio")
        fin = cleaned_data.get("fin")

        if inicio and fin and fin < inicio:
            self.add_error("fin", "La fecha de fin no puede ser anterior a la de inicio.")

        return cleaned_data


class AsignarRepartidorForm(forms.Form):
    repartidor_id = forms.IntegerField(widget=forms.HiddenInput())
    pedido_id = forms.IntegerField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        repartidor_id = cleaned_data.get("repartidor_id")
        pedido_id = cleaned_data.get("pedido_id")

        if repartidor_id:
            try:
                repartidor = User.objects.get(pk=repartidor_id)
            except User.DoesNotExist:
                self.add_error("repartidor_id", "El repartidor no existe.")
            else:
                if not repartidor.is_active:
                    self.add_error("repartidor_id", "El repartidor no está activo.")

        if pedido_id:
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
            except Pedido.DoesNotExist:
                self.add_error("pedido_id", "El pedido no existe.")
            else:
                # El pedido debe estar en estado listo para despacho o en camino
                estados_validos = [
                    Pedido.Estado.LISTO_DESPACHO,
                    Pedido.Estado.EN_CAMINO,
                ]
                if pedido.estado not in estados_validos:
                    self.add_error(
                        "pedido_id",
                        "El pedido debe estar en estado 'Listo para despacho' o 'En camino' para asignar un repartidor."
                    )

                # Verificar que no tenga ya una entrega asignada
                if hasattr(pedido, "entrega"):
                    self.add_error("pedido_id", "Este pedido ya tiene una entrega asignada.")

        return cleaned_data