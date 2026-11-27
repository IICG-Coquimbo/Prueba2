from django.urls import path

from apps.inicio.views import HomeView

app_name = "inicio"

urlpatterns = [
    path("", HomeView.as_view(), name="inicio"),
]
