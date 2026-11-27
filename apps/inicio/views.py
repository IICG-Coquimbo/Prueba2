from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import NoReverseMatch, reverse
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'inicio/home.html'

    def get_login_url(self):
        try:
            return reverse('cuentas:login')
        except NoReverseMatch:
            # En la etapa 2, el superusuario inicia sesión en el admin.
            return reverse('admin:login')
