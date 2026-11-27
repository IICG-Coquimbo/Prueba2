from django.urls import path

from apps.pagos import views

app_name = "pagos"

urlpatterns = [
    path("pasarela/<str:referencia>/", views.PasarelaView.as_view(), name="pasarela"),
]
