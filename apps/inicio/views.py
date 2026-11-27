from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "inicio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Modulos con sus URLs y permisos
        modulos = []

        # Inicio - siempre disponible si está logueado
        modulos.append({
            'nombre': 'Inicio',
            'url_name': 'inicio',
            'perm_check': user.is_authenticated,
        })

        # Catalogo - Menu
        if user.is_authenticated and user.has_perm('catalogo.view_producto'):
            modulos.append({
                'nombre': 'Menu',
                'url_name': 'catalogo:producto_list',
                'perm_check': True,
            })

        # Carrito
        if user.is_authenticated and user.has_perm('pedidos.add_pedido'):
            modulos.append({
                'nombre': 'Carrito',
                'url_name': 'pedidos:carrito',
                'perm_check': True,
            })

        # Pedidos
        if user.is_authenticated and user.has_perm('pedidos.view_pedido'):
            modulos.append({
                'nombre': 'Mis pedidos',
                'url_name': 'pedidos:pedido_list',
                'perm_check': True,
            })

        # Entregas
        if user.is_authenticated and user.has_perm('pedidos.despachar_pedido'):
            modulos.append({
                'nombre': 'Entregas',
                'url_name': 'entregas:entrega_list',
                'perm_check': True,
            })

        # Reportes
        if user.is_authenticated and user.has_perm('pedidos.ver_reportes'):
            modulos.append({
                'nombre': 'Reportes',
                'url_name': 'pedidos:reporte_list',
                'perm_check': True,
            })

        # Mis direcciones
        if user.is_authenticated and user.has_perm('cuentas.view_direccion'):
            modulos.append({
                'nombre': 'Mis direcciones',
                'url_name': 'cuentas:direccion_list',
                'perm_check': True,
            })

        # Administracion (solo staff)
        if user.is_authenticated and user.is_staff:
            modulos.append({
                'nombre': 'Administracion',
                'url_name': 'admin:index',
                'perm_check': True,
            })

        context['modulos'] = modulos
        context['nombre_usuario'] = user.get_full_name() or user.username
        context['grupo'] = [g.name for g in user.groups.all()]

        return context