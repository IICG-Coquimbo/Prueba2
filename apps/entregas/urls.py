from django.urls import path
from . import views

app_name = "entregas"

urlpatterns = [
    path("entregas/", views.EntregaListView.as_view(), name="entrega_list"),
    path("entregas/<int:pk>/", views.EntregaDetailView.as_view(), name="entrega_detail"),
    path("entregas/nuevo/", views.EntregaCreateView.as_view(), name="entrega_create"),
    path("entregas/<int:pk>/editar/", views.EntregaUpdateView.as_view(), name="entrega_update"),
    path("entregas/<int:pk>/borrar/", views.EntregaDeleteView.as_view(), name="entrega_delete"),
]
