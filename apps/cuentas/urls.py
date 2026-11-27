from django.urls import re_path

from . import views


app_name = "cuentas"

urlpatterns = [
    re_path(r"^login/$", views.CuentasLoginView.as_view(), name="login"),
    re_path(r"^logout/$", views.CuentasLogoutView.as_view(), name="logout"),
    re_path(r"^registro/$", views.RegistroView.as_view(), name="registro"),
    re_path(r"^direcciones/$", views.DireccionListView.as_view(), name="direccion_list"),
    re_path(r"^direcciones/nueva/$", views.DireccionCreateView.as_view(), name="direccion_create"),
]
