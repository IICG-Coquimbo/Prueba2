"""Crea los grupos y permisos de docs/roles.md; con --demo, los datos de prueba."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

APPS_CON_MODELOS = [
    "cuentas",
    "catalogo",
    "promociones",
    "pedidos",
    "pagos",
    "entregas",
]

PERMISOS_POR_GRUPO = {
    "Cliente": [
        "catalogo.view_producto",
        "catalogo.view_categoria",
        "pedidos.view_pedido",
        "pedidos.add_pedido",
        "pedidos.change_pedido",
        "pedidos.view_itempedido",
        "pedidos.add_itempedido",
        "pedidos.change_itempedido",
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

CLAVE_DEMO = "clave1234"

USUARIOS_DEMO = [
    ("admin1", "Administrador", True),
    ("barista1", "Barista", False),
    ("repartidor1", "Repartidor", False),
    ("repartidor2", "Repartidor", False),
    ("dueno1", "Dueno", False),
    ("cliente1", "Cliente", False),
]

CATEGORIAS_DEMO = ["Cafe", "Pasteleria"]

PRODUCTOS_DEMO = [
    ("Espresso", "Cafe", "1800", True),
    ("Cappuccino", "Cafe", "2800", True),
    ("Latte", "Cafe", "3000", True),
    ("Croissant", "Pasteleria", "2200", True),
    ("Torta de chocolate", "Pasteleria", "3200", False),
]

OPCIONES_DEMO = [
    ("tamano", "Pequeno", "0"),
    ("tamano", "Mediano", "500"),
    ("tamano", "Grande", "900"),
    ("leche", "Entera", "0"),
    ("leche", "Avena", "600"),
    ("azucar", "Sin azucar", "0"),
    ("azucar", "Con azucar", "0"),
]


class Command(BaseCommand):
    help = "Crea los grupos y permisos de roles.md; con --demo crea usuarios y datos de demostracion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Crea ademas los usuarios y datos de demostracion de docs/roles.md.",
        )

    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_usuarios()
            self.crear_catalogo()
            self.crear_codigo_descuento()
        self.stdout.write(self.style.SUCCESS("crear_roles finalizado."))

    def permisos_desde_codigos(self, codigos):
        permisos = []
        for codigo in codigos:
            app_label, nombre = codigo.split(".", 1)
            permiso = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=nombre,
            ).first()
            if permiso is None:
                self.stdout.write(
                    self.style.WARNING(f"Permiso no encontrado: {codigo}")
                )
            else:
                permisos.append(permiso)
        return permisos

    def crear_grupos(self):
        for nombre, codigos in PERMISOS_POR_GRUPO.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {nombre}"))
            permisos = self.permisos_desde_codigos(codigos)
            grupo.permissions.add(*permisos)
            self.stdout.write(f"  Permisos de {nombre}: {len(permisos)}")

        grupo_admin, creado = Group.objects.get_or_create(name="Administrador")
        if creado:
            self.stdout.write(self.style.SUCCESS("Grupo creado: Administrador"))
        permisos_admin = Permission.objects.filter(
            content_type__app_label__in=APPS_CON_MODELOS
        )
        grupo_admin.permissions.add(*permisos_admin)
        self.stdout.write(
            f"  Permisos de Administrador: {permisos_admin.count()} "
            "(todos los de las 6 apps; 'Es staff' se marca en el usuario)"
        )

    def crear_usuarios(self):
        for username, nombre_grupo, es_staff in USUARIOS_DEMO:
            usuario, creado = User.objects.get_or_create(username=username)
            usuario.set_password(CLAVE_DEMO)
            if es_staff:
                usuario.is_staff = True
            usuario.save()
            grupo, _creado = Group.objects.get_or_create(name=nombre_grupo)
            usuario.groups.add(grupo)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username}"))
            else:
                self.stdout.write(f"  Usuario ya existia: {username}")

        cliente1 = User.objects.get(username="cliente1")
        perfil, creado = PerfilCliente.objects.get_or_create(
            usuario=cliente1,
            defaults={"telefono": "123456789"},
        )
        if creado:
            self.stdout.write(self.style.SUCCESS("PerfilCliente creado: cliente1"))

        direccion, creado = Direccion.objects.get_or_create(
            usuario=cliente1,
            alias="Casa",
            defaults={"direccion": "Direccion de demostracion", "referencia": ""},
        )
        if creado:
            self.stdout.write(self.style.SUCCESS("Direccion creada: Casa (cliente1)"))

    def crear_catalogo(self):
        categorias = {}
        for nombre in CATEGORIAS_DEMO:
            categoria, creado = Categoria.objects.get_or_create(nombre=nombre)
            categorias[nombre] = categoria
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Categoria creada: {nombre}"))

        productos = {}
        for nombre, categoria, precio, disponible in PRODUCTOS_DEMO:
            producto, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categorias[categoria],
                    "precio": Decimal(precio),
                    "disponible": disponible,
                },
            )
            productos[nombre] = producto
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Producto creado: {nombre}"))

        for nombre_producto in ("Cappuccino", "Latte"):
            producto = productos[nombre_producto]
            for tipo, nombre, recargo in OPCIONES_DEMO:
                opcion, creado = OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": Decimal(recargo)},
                )
                if creado:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Opcion creada: {nombre} ({nombre_producto})"
                        )
                    )

    def crear_codigo_descuento(self):
        hoy = date.today()
        codigo, creado = CodigoDescuento.objects.get_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "solo_primer_pedido": True,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
                "activo": True,
            },
        )
        if creado:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Codigo creado: {codigo.codigo} (vigente hasta {codigo.vigente_hasta})"
                )
            )
