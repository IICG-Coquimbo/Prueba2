from django.urls import path

from .views import PagoPasarelaView

app_name = "pagos"

urlpatterns = [
    path("pasarela/<str:referencia>/", PagoPasarelaView.as_view(), name="pasarela"),
]
