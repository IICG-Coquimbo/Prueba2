from django.urls import path

from .views import EntregaListView

app_name = "entregas"

urlpatterns = [
    path("", EntregaListView.as_view(), name="entrega_list"),
]
