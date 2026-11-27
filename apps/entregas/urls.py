from django.urls import path

from . import views

app_name = "entregas"

urlpatterns = [
    path("", views.EntregaListView.as_view(), name="entrega_list"),
]
