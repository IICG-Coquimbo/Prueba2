from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        def agregar(url, label, perm=None, staff=False):
            if staff and not user.is_staff:
                return
            if perm and not user.has_perm(perm):
                return
            ctx.setdefault("modulos", []).append({"url": url, "label": label})

        agregar("inicio", "Inicio")
        agregar("catalogo:producto_list", "Menu", perm="catalogo.view_producto")
        agregar("pedidos:carrito", "Carrito", perm="pedidos.add_pedido")
        label_pedidos = "Mis pedidos" if user.has_perm("pedidos.add_pedido") else "Pedidos"
        agregar("pedidos:pedido_list", label_pedidos, perm="pedidos.view_pedido")
        agregar("cuentas:direccion_list", "Mis direcciones", perm="cuentas.view_direccion")
        agregar("entregas:entrega_list", "Entregas", perm="pedidos.despachar_pedido")
        agregar("reportes:reporte_list", "Reportes", perm="pedidos.ver_reportes")
        agregar("admin:index", "Administracion", staff=True)

        return ctx
