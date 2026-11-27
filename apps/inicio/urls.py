from django.urls import path

from .views import HomeView

app_name = "inicio"

urlpatterns = [
    path("", HomeView.as_view(), name="inicio"),
]
