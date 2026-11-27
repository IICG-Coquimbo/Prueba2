from django.urls import path

from apps.pagos.views import PasarelaView

app_name = "pagos"

urlpatterns = [
    path("pasarela/<str:referencia>/", PasarelaView.as_view(), name="pasarela"),
]
