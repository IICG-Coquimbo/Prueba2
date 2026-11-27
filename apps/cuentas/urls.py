from django.urls import path

from .views import (
    DireccionCreateView,
    DireccionDeleteView,
    DireccionListView,
    DireccionUpdateView,
    LoginView,
    LogoutView,
    RegistroView,
)

app_name = "cuentas"

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("direcciones/", DireccionListView.as_view(), name="direccion_list"),
    path("direcciones/nueva/", DireccionCreateView.as_view(), name="direccion_create"),
    path(
        "direcciones/<int:pk>/editar/",
        DireccionUpdateView.as_view(),
        name="direccion_update",
    ),
    path(
        "direcciones/<int:pk>/borrar/",
        DireccionDeleteView.as_view(),
        name="direccion_delete",
    ),
]
