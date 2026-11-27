from django.urls import path

from pagos.views import PagoListView, PasarelaFormView

app_name = 'pagos'

urlpatterns = [
    path('', PagoListView.as_view(), name='pago_list'),
    path('pasarela/<str:referencia>/', PasarelaFormView.as_view(), name='pasarela'),
]