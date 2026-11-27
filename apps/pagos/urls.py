from django.urls import path
from . import views

app_name = "pagos"

urlpatterns = [
    path("pagos/", views.PagoListView.as_view(), name="pago_list"),
    path("pagos/<int:pk>/", views.PagoDetailView.as_view(), name="pago_detail"),
    path("pagos/nuevo/", views.PagoCreateView.as_view(), name="pago_create"),
    path("pagos/<int:pk>/editar/", views.PagoUpdateView.as_view(), name="pago_update"),
    path("pagos/<int:pk>/borrar/", views.PagoDeleteView.as_view(), name="pago_delete"),
]
