from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

def inicio(request):
    return HttpResponse("Bienvenido a Cafe Rincon - Sistema de Pedidos")

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"
