from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'inicio/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupo = self.request.user.groups.first()
        context['rol'] = grupo.name if grupo else ''
        return context
