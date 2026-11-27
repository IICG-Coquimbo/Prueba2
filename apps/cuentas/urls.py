from django.urls import path

from apps.cuentas.views import (
    CerrarSesionView,
    DireccionCreateView,
    DireccionDeleteView,
    DireccionListView,
    DireccionUpdateView,
    IniciarSesionView,
    RegistroView,
)

app_name = "cuentas"

urlpatterns = [
    path("login/", IniciarSesionView.as_view(), name="login"),
    path("logout/", CerrarSesionView.as_view(), name="logout"),
    path("registro/", RegistroView.as_view(), name="registro"),
    path("direcciones/", DireccionListView.as_view(), name="direccion_list"),
    path("direcciones/nueva/", DireccionCreateView.as_view(), name="direccion_create"),
    path("direcciones/<int:pk>/editar/", DireccionUpdateView.as_view(), name="direccion_update"),
    path("direcciones/<int:pk>/borrar/", DireccionDeleteView.as_view(), name="direccion_delete"),
]
