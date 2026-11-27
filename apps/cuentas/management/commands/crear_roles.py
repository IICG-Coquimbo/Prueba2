from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.cuentas.models import PerfilCliente, Direccion
from apps.catalogo.models import Categoria, Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado
from apps.pagos.models import Pago
from apps.entregas.models import Entrega

from datetime import date, timedelta


PERMISOS_POR_GRUPO = {
    "Cliente": [
        "catalogo.view_producto",
        "catalogo.view_categoria",
        "pedidos.view_pedido",
        "pedidos.add_pedido",
        "pedidos.change_pedido",
        "pedidos.add_itempedido",
        "pedidos.change_itempedido",
        "pedidos.view_itempedido",
        "pedidos.delete_itempedido",
        "cuentas.view_direccion",
        "cuentas.add_direccion",
        "cuentas.change_direccion",
        "cuentas.delete_direccion",
    ],
    "Barista": [
        "pedidos.view_pedido",
        "pedidos.preparar_pedido",
        "catalogo.view_producto",
    ],
    "Repartidor": [
        "pedidos.view_pedido",
        "pedidos.despachar_pedido",
        "entregas.view_entrega",
        "entregas.add_entrega",
        "entregas.change_entrega",
    ],
    "Dueno": [
        "pedidos.ver_reportes",
        "pedidos.view_pedido",
        "entregas.view_entrega",
    ],
}

MODELOS_ADMIN = [
    PerfilCliente, Direccion,
    Categoria, Producto, OpcionProducto,
    CodigoDescuento,
    Pedido, ItemPedido, HistorialEstado,
    Pago,
    Entrega,
]


def obtener_permisos_modelo(modelo):
    ct = ContentType.objects.get_for_model(modelo)
    return Permission.objects.filter(content_type=ct)


class Command(BaseCommand):
    help = "Crea grupos con permisos y, con --demo, usuarios y datos de demostracion segun docs/roles.md."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Ademas crea usuarios de prueba y datos de demostracion.",
        )

    def handle(self, *args, **options):
        demo = options["demo"]

        # 1. Grupos con permisos específicos
        for nombre_grupo, permisos in PERMISOS_POR_GRUPO.items():
            grupo, creado = Group.objects.get_or_create(name=nombre_grupo)
            if creado:
                self.stdout.write(f"Grupo '{nombre_grupo}' creado.")
            grupo.permissions.clear()
            for codperm in permisos:
                app_label, codename = codperm.split(".")
                try:
                    permiso = Permission.objects.get(
                        content_type__app_label=app_label, codename=codename
                    )
                    grupo.permissions.add(permiso)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Permiso no encontrado: {codperm}")
                    )
            self.stdout.write(
                f"Grupo '{nombre_grupo}' con {grupo.permissions.count()} permisos."
            )

        # 2. Grupo Administrador: TODOS los permisos de todas las apps
        grupo_admin, _ = Group.objects.get_or_create(name="Administrador")
        grupo_admin.permissions.clear()
        for modelo in MODELOS_ADMIN:
            for permiso in obtener_permisos_modelo(modelo):
                grupo_admin.permissions.add(permiso)
        # Agregar permisos propios de Pedido
        for codename in ["preparar_pedido", "despachar_pedido", "ver_reportes"]:
            try:
                permiso = Permission.objects.get(
                    content_type__app_label="pedidos", codename=codename
                )
                grupo_admin.permissions.add(permiso)
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Permiso propio no encontrado: pedidos.{codename}")
                )
        self.stdout.write(
            f"Grupo 'Administrador' con {grupo_admin.permissions.count()} permisos."
        )

        if not demo:
            self.stdout.write(self.style.SUCCESS("Grupos creados/actualizados."))
            return

        # 3. Usuarios de prueba
        clave_demo = "clave1234"
        USUARIOS_DEMO = [
            ("admin1", "Administrador"),
            ("barista1", "Barista"),
            ("repartidor1", "Repartidor"),
            ("repartidor2", "Repartidor"),
            ("dueno1", "Dueno"),
            ("cliente1", "Cliente"),
        ]

        for username, rol in USUARIOS_DEMO:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if creado:
                user.set_password(clave_demo)
                user.save()
                self.stdout.write(f"Usuario '{username}' ({rol}) creado.")
            else:
                user.set_password(clave_demo)
                user.save()
                self.stdout.write(f"Usuario '{username}' ({rol}) actualizado.")

            grupo = Group.objects.get(name=rol)
            user.groups.clear()
            user.groups.add(grupo)

            if rol == "Administrador":
                user.is_staff = True
                user.save()

            if rol == "Cliente":
                PerfilCliente.objects.get_or_create(
                    usuario=user, defaults={"telefono": ""}
                )

        # Direccion Casa para cliente1
        cliente1 = User.objects.get(username="cliente1")
        Direccion.objects.get_or_create(
            usuario=cliente1,
            alias="Casa",
            defaults={"direccion": "Calle Principal 123", "referencia": "Casa"},
        )
        self.stdout.write("Direccion 'Casa' asignada a cliente1.")

        # 4. Datos de demostracion
        cat_cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
        cat_pasteleria, _ = Categoria.objects.get_or_create(nombre="Pasteleria")

        productos_demo = [
            ("Espresso", cat_cafe, 1800, True),
            ("Cappuccino", cat_cafe, 2800, True),
            ("Latte", cat_cafe, 3000, True),
            ("Croissant", cat_pasteleria, 2200, True),
            ("Torta de chocolate", cat_pasteleria, 3200, False),
        ]
        for nombre, categoria, precio, disponible in productos_demo:
            Producto.objects.get_or_create(
                nombre=nombre,
                categoria=categoria,
                defaults={"precio": precio, "disponible": disponible},
            )
        self.stdout.write("Productos de demostracion creados.")

        # Opciones para Cappuccino y Latte
        for prod_nombre in ["Cappuccino", "Latte"]:
            prod = Producto.objects.get(nombre=prod_nombre)
            opciones_demo = [
                ("tamano", "Pequeno", 0),
                ("tamano", "Mediano", 500),
                ("tamano", "Grande", 900),
                ("leche", "Entera", 0),
                ("leche", "Avena", 600),
                ("azucar", "Sin azucar", 0),
                ("azucar", "Con azucar", 0),
            ]
            for tipo, nombre_op, recargo in opciones_demo:
                OpcionProducto.objects.get_or_create(
                    producto=prod,
                    tipo=tipo,
                    nombre=nombre_op,
                    defaults={"recargo": recargo},
                )
        self.stdout.write("Opciones de producto creadas.")

        # Codigo descuento BIENVENIDA10
        hoy = date.today()
        CodigoDescuento.objects.get_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
                "solo_primer_pedido": True,
                "activo": True,
            },
        )
        self.stdout.write("Codigo BIENVENIDA10 creado.")

        self.stdout.write(self.style.SUCCESS("Datos de demostracion creados."))
        self.stdout.write(
            self.style.SUCCESS(f"Clave de usuarios demo: {clave_demo}")
        )
