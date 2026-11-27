from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupos = self.request.user.groups.values_list("name", flat=True)
        context["rol"] = ", ".join(grupos) if grupos else "Sin rol asignado"
        return context
