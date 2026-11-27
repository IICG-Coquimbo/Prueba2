from django.urls import path

from apps.entregas.views import EntregaListView

app_name = "entregas"

urlpatterns = [
    path("entregas/", EntregaListView.as_view(), name="entrega_list"),
]
