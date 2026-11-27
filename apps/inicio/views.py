from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        grupo = user.groups.first()
        context["rol"] = grupo.name if grupo else "Sin rol"
        context["menu"] = user.has_perm("catalogo.view_producto")
        context["carrito"] = user.has_perm("pedidos.add_pedido")
        context["pedidos"] = user.has_perm("pedidos.view_pedido")
        context["entregas"] = user.has_perm("pedidos.despachar_pedido")
        context["reportes"] = user.has_perm("pedidos.ver_reportes")
        context["direcciones"] = user.has_perm("cuentas.view_direccion")
        context["administracion"] = user.is_staff
        return context
