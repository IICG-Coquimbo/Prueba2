from django.urls import path
from .views import EntregaListView, EntregaDetailView

app_name = 'entregas'

urlpatterns = [
    path('', EntregaListView.as_view(), name='entrega_list'),
    path('<int:pk>/', EntregaDetailView.as_view(), name='entrega_detail'),
]