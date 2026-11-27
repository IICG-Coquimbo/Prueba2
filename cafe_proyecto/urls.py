"""
URL configuration for cafe_proyecto project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('logout/', LogoutView.as_view(),name='logout'),
    re_path(r'^', include('apps.inicio.urls')),
    re_path(r'^menu/', include('apps.catalogo.urls')),
    re_path(r'^pedidos/', include('apps.pedidos.urls')),
    re_path(r'^cuentas/', include('apps.cuentas.urls')),
    re_path(r'^pagos/', include('apps.pagos.urls')),
    re_path(r'^admin/', admin.site.urls),
]