from django.urls import path

from .views import CuentasLoginView, CuentasLogoutView, RegistroView

app_name = "cuentas"

urlpatterns = [
    path("login/", CuentasLoginView.as_view(), name="login"),
    path("logout/", CuentasLogoutView.as_view(), name="logout"),
    path("registro/", RegistroView.as_view(), name="registro"),
]
