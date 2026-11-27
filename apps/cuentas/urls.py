from django.urls import path

from django.contrib.auth.views import LoginView, LogoutView

from . import views
from .forms import LoginForm

app_name = "cuentas"

urlpatterns = [
    path("login/", LoginView.as_view(
        authentication_form=LoginForm,
        template_name="cuentas/login.html",
    ), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("direcciones/", views.DireccionListView.as_view(), name="direccion_list"),
    path("direcciones/nueva/", views.DireccionCreateView.as_view(), name="direccion_create"),
    path("direcciones/<int:pk>/editar/", views.DireccionUpdateView.as_view(), name="direccion_update"),
    path("direcciones/<int:pk>/borrar/", views.DireccionDeleteView.as_view(), name="direccion_delete"),
]
