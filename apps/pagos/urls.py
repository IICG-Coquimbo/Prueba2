from django.urls import re_path

from . import views


app_name = "pagos"

urlpatterns = [
    re_path(r"^pasarela/(?P<referencia>[^/]+)/$", views.PasarelaView.as_view(), name="pasarela"),
]
