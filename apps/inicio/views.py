from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import NoReverseMatch, reverse
from django.views.generic import TemplateView


MODULOS = [
    {"nombre": "Menu", "url_name": "catalogo:producto_list", "permiso": "catalogo.view_producto"},
    {"nombre": "Carrito", "url_name": "pedidos:carrito_detail", "permiso": "pedidos.add_pedido"},
    {"nombre": "Pedidos", "url_name": "pedidos:pedido_list", "permiso": "pedidos.view_pedido"},
    {"nombre": "Entregas", "url_name": "entregas:entrega_list", "permiso": "pedidos.despachar_pedido"},
    {"nombre": "Reportes", "url_name": "reportes:reporte_panel", "permiso": "pedidos.ver_reportes"},
    {"nombre": "Mis direcciones", "url_name": "cuentas:direccion_list", "permiso": "cuentas.view_direccion"},
    {"nombre": "Administracion", "url_name": "admin:index", "permiso": None, "staff_only": True},
]


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        grupo = user.groups.first()

        context["rol"] = grupo.name if grupo else "Sin rol"

        modulos = []
        for modulo in MODULOS:
            if modulo.get("staff_only", False):
                accesible = user.is_staff
            else:
                accesible = user.has_perm(modulo["permiso"])
            if not accesible:
                continue
            try:
                url = reverse(modulo["url_name"])
            except NoReverseMatch:
                continue
            modulos.append({**modulo, "url": url})

        context["modulos"] = modulos
        return context
