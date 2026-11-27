from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import NoReverseMatch, reverse
from django.views.generic import TemplateView


MODULOS = [
    ("catalogo:producto_list", "catalogo.view_producto"),
    ("pedidos:carrito_detail", "pedidos.add_pedido"),
    ("pedidos:pedido_list", "pedidos.view_pedido"),
    ("entregas:entrega_list", "pedidos.despachar_pedido"),
    ("reportes:reporte_panel", "pedidos.ver_reportes"),
    ("cuentas:direccion_list", "cuentas.view_direccion"),
]


def url_exists(name):
    try:
        reverse(name)
    except NoReverseMatch:
        return False
    return True


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["tiene_modulos"] = any(
            url_exists(name) and user.has_perm(perm)
            for name, perm in MODULOS
        ) or (url_exists("admin:index") and user.is_staff)
        return context
