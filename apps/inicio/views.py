from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["usuario"] = self.request.user
        # Obtener el grupo/rol del usuario
        grupos = self.request.user.groups.all()
        context["rol"] = grupos.first().name if grupos.exists() else "Sin rol"
        return context