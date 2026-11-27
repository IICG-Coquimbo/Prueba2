from django.urls import path
from . import views
from .views import CustomLoginView, CustomLogoutView

app_name = "cuentas"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("perfil/", views.perfil, name="perfil"),
    path("direcciones/", views.direcciones, name="direcciones"),
]