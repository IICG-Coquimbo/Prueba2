from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

CLAVE_DEMO = 'clave1234'
APPS_ADMINISTRADOR = [
    'cuentas',
    'catalogo',
    'promociones',
    'pedidos',
    'pagos',
    'entregas',
]


class Command(BaseCommand):
    help = 'Crea los roles y, con --demo, usuarios y datos de demostracion.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Crea tambien los usuarios y datos de demostracion.',
        )

    def handle(self, *args, **options):
        self.crear_grupos()
        if options['demo']:
            self.crear_usuarios_demo()
            self.crear_datos_demo()
        self.stdout.write(self.style.SUCCESS('crear_roles finalizado.'))

    def permisos_por_codigo(self, codigos):
        permisos = []
        for codigo in codigos:
            app_label, nombre = codigo.split('.')
            try:
                permisos.append(
                    Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=nombre,
                    )
                )
            except Permission.DoesNotExist:
                raise CommandError(f'Falta el permiso {codigo}. Ejecuta migrate primero.')
        return permisos

    def crear_grupos(self):
        definiciones = [
            (
                'Cliente',
                [
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
                ],
            ),
            (
                'Barista',
                [
                    'pedidos.view_pedido',
                    'pedidos.preparar_pedido',
                    'catalogo.view_producto',
                ],
            ),
            (
                'Repartidor',
                [
                    'pedidos.view_pedido',
                    'pedidos.despachar_pedido',
                    'entregas.view_entrega',
                    'entregas.add_entrega',
                    'entregas.change_entrega',
                ],
            ),
            ('Administrador', None),
            (
                'Dueno',
                [
                    'pedidos.ver_reportes',
                    'pedidos.view_pedido',
                    'entregas.view_entrega',
                ],
            ),
        ]

        for nombre, codigos in definiciones:
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(f'Grupo creado: {nombre}')
            if codigos is None:
                permisos = list(
                    Permission.objects.filter(
                        content_type__app_label__in=APPS_ADMINISTRADOR
                    )
                )
            else:
                permisos = self.permisos_por_codigo(codigos)
            grupo.permissions.set(permisos)
            self.stdout.write(f'{nombre}: {len(permisos)} permisos asignados.')

    def crear_usuarios_demo(self):
        definiciones = [
            ('admin1', 'Administrador', True),
            ('barista1', 'Barista', False),
            ('repartidor1', 'Repartidor', False),
            ('repartidor2', 'Repartidor', False),
            ('dueno1', 'Dueno', False),
            ('cliente1', 'Cliente', False),
        ]

        for username, nombre_grupo, es_staff in definiciones:
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={'is_staff': es_staff},
            )
            campos = []
            if creado:
                usuario.set_password(CLAVE_DEMO)
                campos.append('password')
                self.stdout.write(f'Usuario creado: {username}')
            elif not usuario.check_password(CLAVE_DEMO):
                usuario.set_password(CLAVE_DEMO)
                campos.append('password')
            if usuario.is_staff != es_staff:
                usuario.is_staff = es_staff
                campos.append('is_staff')
            if campos:
                usuario.save(update_fields=campos)

            grupo = Group.objects.get(name=nombre_grupo)
            usuario.groups.set([grupo])
            self.stdout.write(f'{username} asignado al grupo {nombre_grupo}.')

            if username == 'cliente1':
                self.crear_perfil_cliente(usuario)

    def crear_perfil_cliente(self, usuario):
        perfil, creado = PerfilCliente.objects.get_or_create(
            usuario=usuario,
            defaults={'telefono': '912345678'},
        )
        if creado:
            self.stdout.write(f'Perfil creado: {usuario.username}')
        elif perfil.telefono != '912345678':
            perfil.telefono = '912345678'
            perfil.save(update_fields=['telefono'])

        direccion, creado = Direccion.objects.get_or_create(
            usuario=usuario,
            alias='Casa',
            defaults={'direccion': 'Av. Principal 123', 'referencia': ''},
        )
        campos = []
        if direccion.direccion != 'Av. Principal 123':
            direccion.direccion = 'Av. Principal 123'
            campos.append('direccion')
        if direccion.referencia != '':
            direccion.referencia = ''
            campos.append('referencia')
        if campos:
            direccion.save(update_fields=campos)
        if creado:
            self.stdout.write(f'Direccion creada: {direccion.alias}')

    def crear_datos_demo(self):
        cafe, _ = Categoria.objects.get_or_create(nombre='Cafe')
        pasteleria, _ = Categoria.objects.get_or_create(nombre='Pasteleria')
        self.stdout.write('Categorias listas: Cafe, Pasteleria.')

        productos = [
            ('Espresso', cafe, Decimal('1800'), True),
            ('Cappuccino', cafe, Decimal('2800'), True),
            ('Latte', cafe, Decimal('3000'), True),
            ('Croissant', pasteleria, Decimal('2200'), True),
            ('Torta de chocolate', pasteleria, Decimal('3200'), False),
        ]
        por_nombre = {}
        for nombre, categoria, precio, disponible in productos:
            producto, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'categoria': categoria,
                    'precio': precio,
                    'disponible': disponible,
                },
            )
            campos = []
            if producto.categoria_id != categoria.pk:
                producto.categoria = categoria
                campos.append('categoria')
            if producto.precio != precio:
                producto.precio = precio
                campos.append('precio')
            if producto.disponible != disponible:
                producto.disponible = disponible
                campos.append('disponible')
            if campos:
                producto.save(update_fields=campos)
            if creado:
                self.stdout.write(f'Producto creado: {nombre}')
            por_nombre[nombre] = producto

        opciones = [
            (OpcionProducto.Tipo.TAMANO, 'Pequeno', Decimal('0')),
            (OpcionProducto.Tipo.TAMANO, 'Mediano', Decimal('500')),
            (OpcionProducto.Tipo.TAMANO, 'Grande', Decimal('900')),
            (OpcionProducto.Tipo.LECHE, 'Entera', Decimal('0')),
            (OpcionProducto.Tipo.LECHE, 'Avena', Decimal('600')),
            (OpcionProducto.Tipo.AZUCAR, 'Sin azucar', Decimal('0')),
            (OpcionProducto.Tipo.AZUCAR, 'Con azucar', Decimal('0')),
        ]
        for nombre_producto in ('Cappuccino', 'Latte'):
            producto = por_nombre[nombre_producto]
            for tipo, nombre_opcion, recargo in opciones:
                opcion, creado = OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre_opcion,
                    defaults={'recargo': recargo},
                )
                if opcion.recargo != recargo:
                    opcion.recargo = recargo
                    opcion.save(update_fields=['recargo'])
                if creado:
                    self.stdout.write(
                        f'Opcion creada: {nombre_opcion} ({nombre_producto})'
                    )

        hoy = timezone.localdate()
        codigo, creado = CodigoDescuento.objects.get_or_create(
            codigo='BIENVENIDA10',
            defaults={
                'porcentaje': 10,
                'solo_primer_pedido': True,
                'vigente_desde': hoy,
                'vigente_hasta': hoy + timedelta(days=60),
                'activo': True,
            },
        )
        campos = []
        if codigo.porcentaje != 10:
            codigo.porcentaje = 10
            campos.append('porcentaje')
        if not codigo.solo_primer_pedido:
            codigo.solo_primer_pedido = True
            campos.append('solo_primer_pedido')
        if codigo.vigente_desde != hoy:
            codigo.vigente_desde = hoy
            campos.append('vigente_desde')
        if codigo.vigente_hasta != hoy + timedelta(days=60):
            codigo.vigente_hasta = hoy + timedelta(days=60)
            campos.append('vigente_hasta')
        if not codigo.activo:
            codigo.activo = True
            campos.append('activo')
        if campos:
            codigo.save(update_fields=campos)
        if creado:
            self.stdout.write('Codigo creado: BIENVENIDA10')
