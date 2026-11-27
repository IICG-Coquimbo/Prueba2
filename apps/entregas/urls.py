from django.urls import path

from entregas.views import EntregaListView, EntregaDetailView, EntregaAssignView

app_name = 'entregas'

urlpatterns = [
    path('', EntregaListView.as_view(), name='list'),
    path('<int:pk>/', EntregaDetailView.as_view(), name='detail'),
    path('<int:pk>/asignar/', EntregaAssignView.as_view(), name='asignar'),
]