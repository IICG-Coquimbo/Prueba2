from django.urls import path
from . import views

app_name = "catalogo"

urlpatterns = [
    path("categorias/", views.CategoriaListView.as_view(), name="categoria_list"),
    path("categorias/nuevo/", views.CategoriaCreateView.as_view(), name="categoria_create"),
    path("categorias/<int:pk>/", views.CategoriaDetailView.as_view(), name="categoria_detail"),
    path("categorias/<int:pk>/editar/", views.CategoriaUpdateView.as_view(), name="categoria_update"),
    path("categorias/<int:pk>/borrar/", views.CategoriaDeleteView.as_view(), name="categoria_delete"),
    path("productos/", views.ProductoListView.as_view(), name="producto_list"),
    path("productos/nuevo/", views.ProductoCreateView.as_view(), name="producto_create"),
    path("productos/<int:pk>/", views.ProductoDetailView.as_view(), name="producto_detail"),
    path("productos/<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="producto_update"),
    path("productos/<int:pk>/borrar/", views.ProductoDeleteView.as_view(), name="producto_delete"),
    path("opciones/", views.OpcionProductoListView.as_view(), name="opcionproducto_list"),
    path("opciones/nuevo/", views.OpcionProductoCreateView.as_view(), name="opcionproducto_create"),
    path("opciones/<int:pk>/", views.OpcionProductoDetailView.as_view(), name="opcionproducto_detail"),
    path("opciones/<int:pk>/editar/", views.OpcionProductoUpdateView.as_view(), name="opcionproducto_update"),
    path("opciones/<int:pk>/borrar/", views.OpcionProductoDeleteView.as_view(), name="opcionproducto_delete"),
]
