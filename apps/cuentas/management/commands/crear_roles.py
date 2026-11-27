from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.cuentas.models import PerfilCliente, Direccion


def assign_permissions_to_group(group, permission_codes):
    """Asigna permisos a un grupo, quitando los que ya tenga."""
    current = set(group.permissions.values_list('codename', flat=True))
    desired = set(permission_codes)
    to_add = desired - current
    to_remove = current - desired
    if to_add:
        perms = Permission.objects.filter(codename__in=to_add)
        group.permissions.add(*perms)
    if to_remove:
        perms = Permission.objects.filter(codename__in=to_remove)
        group.permissions.remove(*perms)


def get_content_type(app_label, model_name):
    return ContentType.objects.get(app_label=app_label, model=model_name.lower())


def create_permission(codename, name, content_type):
    """Crea un permiso si no existe."""
    Permission.objects.get_or_create(
        codename=codename,
        content_type=content_type,
        defaults={'name': name},
    )


class Command(BaseCommand):
    help='Crea grupos y permisos según docs/roles.md. Uso: python manage.py crear_roles [--demo]'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Crear usuarios de demostracion y datos adicionales',
        )

    def handle(self, *args, **options):
        demo = options['demo']

        # --- Siempre: crear grupos y permisos ---

        # Permisos por app (formato: <app>.<accion>_<modelo>)
        # Apps: cuentas, catalogo, promociones, pedidos, pagos, entregas

        # Cuentas app
        cuentas_ct = get_content_type('cuentas', 'PerfilCliente')
        create_permission('view_perfilcliente', 'Can view perfilcliente', cuentas_ct)
        create_permission('add_perfilcliente', 'Can add perfilcliente', cuentas_ct)
        create_permission('change_perfilcliente', 'Can change perfilcliente', cuentas_ct)
        create_permission('delete_perfilcliente', 'Can delete perfilcliente', cuentas_ct)

        cuentas_direc_ct = get_content_type('cuentas', 'Direccion')
        create_permission('view_direccion', 'Can view direccion', cuentas_direc_ct)
        create_permission('add_direccion', 'Can add direccion', cuentas_direc_ct)
        create_permission('change_direccion', 'Can change direccion', cuentas_direc_ct)
        create_permission('delete_direccion', 'Can delete direccion', cuentas_direc_ct)

        # Catalogo app
        cat_ct = get_content_type('catalogo', 'Categoria')
        create_permission('view_categoria', 'Can view categoria', cat_ct)

        prod_ct = get_content_type('catalogo', 'Producto')
        create_permission('view_producto', 'Can view producto', prod_ct)
        create_permission('add_producto', 'Can add producto', prod_ct)
        create_permission('change_producto', 'Can change producto', prod_ct)
        create_permission('delete_producto', 'Can delete producto', prod_ct)

        opc_ct = get_content_type('catalogo', 'OpcionProducto')
        create_permission('view_opcionproducto', 'Can view opcionproducto', opc_ct)
        create_permission('add_opcionproducto', 'Can add opcionproducto', opc_ct)
        create_permission('change_opcionproducto', 'Can change opcionproducto', opc_ct)
        create_permission('delete_opcionproducto', 'Can delete opcionproducto', opc_ct)

        # Promociones app
        promo_ct = get_content_type('promociones', 'CodigoDescuento')
        create_permission('view_codigodescuento', 'Can view codigo_descuento', promo_ct)
        create_permission('add_codigodescuento', 'Can add codigo_descuento', promo_ct)
        create_permission('change_codigodescuento', 'Can change codigo_descuento', promo_ct)
        create_permission('delete_codigodescuento', 'Can delete codigo_descuento', promo_ct)

        # Pedidos app
        ped_ct = get_content_type('pedidos', 'Pedido')
        create_permission('view_pedido', 'Can view pedido', ped_ct)
        create_permission('add_pedido', 'Can add pedido', ped_ct)
        create_permission('change_pedido', 'Can change pedido', ped_ct)
        create_permission('delete_pedido', 'Can delete pedido', ped_ct)

        item_ct = get_content_type('pedidos', 'ItemPedido')
        create_permission('view_itempedido', 'Can view itempedido', item_ct)
        create_permission('add_itempedido', 'Can add itempedido', item_ct)
        create_permission('change_itempedido', 'Can change itempedido', item_ct)
        create_permission('delete_itempedido', 'Can delete itempedido', item_ct)

        hist_ct = get_content_type('pedidos', 'HistorialEstado')
        create_permission('view_historialestado', 'Can view historialestado', hist_ct)

        # Pagos app
        pag_ct = get_content_type('pagos', 'Pago')
        create_permission('view_pago', 'Can view pago', pag_ct)
        create_permission('add_pago', 'Can add pago', pag_ct)
        create_permission('change_pago', 'Can change pago', pag_ct)
        create_permission('delete_pago', 'Can delete pago', pag_ct)

        # Entregas app
        ent_ct = get_content_type('entregas', 'Entrega')
        create_permission('view_entrega', 'Can view entrega', ent_ct)
        create_permission('add_entrega', 'Can add entrega', ent_ct)
        create_permission('change_entrega', 'Can change entrega', ent_ct)
        create_permission('delete_entrega', 'Can delete entrega', ent_ct)

        # Permisos propios del modelo Pedido (Meta.permissions)
        create_permission('preparar_pedido', 'Can preparar pedido', ped_ct)
        create_permission('despachar_pedido', 'Can despachar pedido', ped_ct)
        create_permission('ver_reportes', 'Can ver reportes', ped_ct)

        # --- Crear grupos y asignar permisos ---

        # Grupo Cliente
        cliente_group, _ = Group.objects.get_or_create(name='Cliente')
        cliente_perms = [
            'catalogo.view_producto',
            'catalogo.view_categoria',
            'pedidos.view_pedido',
            'pedidos.add_pedido',
            'pedidos.change_pedido',
            'pedidos.view_itempedido',
            'pedidos.add_itempedido',
            'pedidos.change_itempedido',
            'pedidos.delete_itempedido',
            'cuentas.view_direccion',
            'cuentas.add_direccion',
            'cuentas.change_direccion',
            'cuentas.delete_direccion',
        ]
        assign_permissions_to_group(cliente_group, cliente_perms)
        self.stdout.write(self.style.SUCCESS(f'Grupo "Cliente" creado/actualizado con {len(cliente_perms)} permisos'))

        # Grupo Barista
        barista_group, _ = Group.objects.get_or_create(name='Barista')
        barista_perms = [
            'pedidos.view_pedido',
            'pedidos.preparar_pedido',
            'catalogo.view_producto',
        ]
        assign_permissions_to_group(barista_group, barista_perms)
        self.stdout.write(self.style.SUCCESS(f'Grupo "Barista" creado/actualizado con {len(barista_perms)} permisos'))

        # Grupo Repartidor
        repartidor_group, _ = Group.objects.get_or_create(name='Repartidor')
        repartidor_perms = [
            'pedidos.view_pedido',
            'pedidos.despachar_pedido',
            'entregas.view_entrega',
            'entregas.add_entrega',
            'entregas.change_entrega',
        ]
        assign_permissions_to_group(repartidor_group, repartidor_perms)
        self.stdout.write(self.style.SUCCESS(f'Grupo "Repartidor" creado/actualizado con {len(repartidor_perms)} permisos'))

        # Grupo Administrador - TODOS los permisos
        admin_group, _ = Group.objects.get_or_create(name='Administrador')
        all_perms = []
        for app_label, model_names in [
            ('cuentas', ['PerfilCliente', 'Direccion']),
            ('catalogo', ['Categoria', 'Producto', 'OpcionProducto']),
            ('promociones', ['CodigoDescuento']),
            ('pedidos', ['Pedido', 'ItemPedido', 'HistorialEstado']),
            ('pagos', ['Pago']),
            ('entregas', ['Entrega']),
        ]:
            for model_name in model_names:
                ct = get_content_type(app_label, model_name)
                for action in ['view', 'add', 'change', 'delete']:
                    codename = f'{action}_{model_name.lower()}'
                    all_perms.append(codename)
        # Add custom permissions
        all_perms.extend(['pedidos.preparar_pedido', 'pedidos.despachar_pedido', 'pedidos.ver_reportes'])
        assign_permissions_to_group(admin_group, all_perms)
        self.stdout.write(self.style.SUCCESS(f'Grupo "Administrador" creado/actualizado con {len(all_perms)} permisos'))

        # Grupo Dueno
        dueño_group, _ = Group.objects.get_or_create(name='Dueño')
        dueño_perms = [
            'pedidos.ver_reportes',
            'pedidos.view_pedido',
            'entregas.view_entrega',
        ]
        assign_permissions_to_group(dueño_group, dueño_perms)
        self.stdout.write(self.style.SUCCESS(f'Grupo "Dueño" creado/actualizado con {len(dueño_perms)} permisos'))

        self.stdout.write(self.style.SUCCESS('Grupos y permisos creados exitosamente.'))

        # --- Con --demo: crear usuarios de prueba ---

        if demo:
            # Usuario admin1
            admin_user, created = User.objects.get_or_create(
                username='admin1',
                defaults={'first_name': 'Admin', 'last_name': 'User', 'email': 'admin@test.com'}
            )
            if created:
                admin_user.set_password('clave1234')
                admin_user.save()
            admin_group = Group.objects.get(name='Administrador')
            admin_user.groups.add(admin_group)
            if created:
                self.stdout.write(self.style.SUCCESS('Usuario admin1 creado'))

            # Usuario barista1
            barista_user, created = User.objects.get_or_create(
                username='barista1',
                defaults={'first_name': 'Barista', 'last_name': 'User', 'email': 'barista@test.com'}
            )
            if created:
                barista_user.set_password('clave1234')
                barista_user.save()
            barista_group = Group.objects.get(name='Barista')
            barista_user.groups.add(barista_group)
            if created:
                self.stdout.write(self.style.SUCCESS('Usuario barista1 creado'))

            # Usuarios repartidor1 y repartidor2
            for i in range(1, 3):
                user, created = User.objects.get_or_create(
                    username=f'repartidor{i}',
                    defaults={'first_name': 'Repartidor', 'last_name': f'User{i}', 'email': f'repartidor{i}@test.com'}
                )
                if created:
                    user.set_password('clave1234')
                    user.save()
                repartidor_group = Group.objects.get(name='Repartidor')
                user.groups.add(repartidor_group)
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Usuario repartidor{i} creado'))

            # Usuario cliente1 con PerfilCliente y direccion "Casa"
            cliente_user, created = User.objects.get_or_create(
                username='cliente1',
                defaults={'first_name': 'Cliente', 'last_name': 'User', 'email': 'cliente@test.com'}
            )
            if created:
                cliente_user.set_password('clave1234')
                cliente_user.save()
            cliente_group = Group.objects.get(name='Cliente')
            cliente_user.groups.add(cliente_group)
            # Crear perfil
            PerfilCliente.objects.get_or_create(usuario=cliente_user)
            # Crear direccion "Casa"
            Direccion.objects.get_or_create(
                usuario=cliente_user,
                alias='Casa',
                direccion='Direccion de prueba',
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Usuario cliente1 creado con perfil y direccion'))

            self.stdout.write(self.style.SUCCESS('Usuarios de demostracion creados exitosamente.'))