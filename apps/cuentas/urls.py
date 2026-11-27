from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from apps.cuentas.forms import LoginForm
from .views import RegistroView, DireccionListView, DireccionCreateView, DireccionUpdateView, DireccionDeleteView

app_name = "cuentas"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="cuentas/login.html", authentication_form=LoginForm), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("registro/", RegistroView.as_view(), name="registro"),
    path("direcciones/", DireccionListView.as_view(), name="direccion_list"),
    path("direcciones/nueva/", DireccionCreateView.as_view(), name="direccion_create"),
    path("direcciones/<int:pk>/editar/", DireccionUpdateView.as_view(), name="direccion_update"),
    path("direcciones/<int:pk>/borrar/", DireccionDeleteView.as_view(), name="direccion_delete"),
]
