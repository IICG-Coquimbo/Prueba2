from django.urls import path
from .views import CustomLoginView, RegistroView, CustomLogoutView

app_name = 'cuentas'
urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('registro/', RegistroView.as_view(), name='registro'),
]