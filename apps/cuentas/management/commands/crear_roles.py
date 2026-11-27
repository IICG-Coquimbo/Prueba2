from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto, TipoOpcion
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

APPS_ADMIN = [
    "cuentas",
    "catalogo",
    "promociones",
    "pedidos",
    "pagos",
    "entregas",
]

GRUPOS = {
    "Cliente": [
        ("catalogo", "view_producto"),
        ("catalogo", "view_categoria"),
        ("pedidos", "view_pedido"),
        ("pedidos", "add_pedido"),
        ("pedidos", "change_pedido"),
        ("pedidos", "view_itempedido"),
        ("pedidos", "add_itempedido"),
        ("pedidos", "change_itempedido"),
        ("pedidos", "delete_itempedido"),
        ("cuentas", "view_direccion"),
        ("cuentas", "add_direccion"),
        ("cuentas", "change_direccion"),
        ("cuentas", "delete_direccion"),
    ],
    "Barista": [
        ("pedidos", "view_pedido"),
        ("pedidos", "preparar_pedido"),
        ("catalogo", "view_producto"),
    ],
    "Repartidor": [
        ("pedidos", "view_pedido"),
        ("pedidos", "despachar_pedido"),
        ("entregas", "view_entrega"),
        ("entregas", "add_entrega"),
        ("entregas", "change_entrega"),
    ],
    "Administrador": None,
    "Dueno": [
        ("pedidos", "ver_reportes"),
        ("pedidos", "view_pedido"),
        ("entregas", "view_entrega"),
    ],
}

USUARIOS_DEMO = [
    ("admin1", "Administrador", True),
    ("barista1", "Barista", False),
    ("repartidor1", "Repartidor", False),
    ("repartidor2", "Repartidor", False),
    ("dueno1", "Dueno", False),
    ("cliente1", "Cliente", False),
]

PRODUCTOS_DEMO = [
    ("Espresso", "Cafe", "1800.00", True),
    ("Cappuccino", "Cafe", "2800.00", True),
    ("Latte", "Cafe", "3000.00", True),
    ("Croissant", "Pasteleria", "2200.00", True),
    ("Torta de chocolate", "Pasteleria", "3200.00", False),
]

OPCIONES_DEMO = [
    (TipoOpcion.TAMANO, "Pequeno", "0.00"),
    (TipoOpcion.TAMANO, "Mediano", "500.00"),
    (TipoOpcion.TAMANO, "Grande", "900.00"),
    (TipoOpcion.LECHE, "Entera", "0.00"),
    (TipoOpcion.LECHE, "Avena", "600.00"),
    (TipoOpcion.AZUCAR, "Sin azucar", "0.00"),
    (TipoOpcion.AZUCAR, "Con azucar", "0.00"),
]


class Command(BaseCommand):
    help = "Crea los grupos con sus permisos y, con --demo, los datos de demostracion."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true")

    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_datos_demo()

    def avisar(self, creado, etiqueta):
        verbo = "Creado" if creado else "Actualizado"
        self.stdout.write(f"{verbo}: {etiqueta}")

    def crear_grupos(self):
        for nombre, pares in GRUPOS.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if pares is None:
                permisos = Permission.objects.filter(
                    content_type__app_label__in=APPS_ADMIN
                )
            else:
                consulta = Q()
                for app_label, codename in pares:
                    consulta |= Q(content_type__app_label=app_label, codename=codename)
                permisos = Permission.objects.filter(consulta)
            grupo.permissions.set(permisos)
            self.avisar(
                creado,
                f"grupo {nombre} ({grupo.permissions.count()} permisos)",
            )

    def crear_datos_demo(self):
        grupos = {grupo.name: grupo for grupo in Group.objects.all()}
        for username, nombre_grupo, es_staff in USUARIOS_DEMO:
            usuario, creado = User.objects.get_or_create(username=username)
            usuario.is_staff = es_staff
            usuario.set_password("clave1234")
            usuario.save()
            usuario.groups.set([grupos[nombre_grupo]])
            self.avisar(creado, f"usuario {username}")

        cliente = User.objects.get(username="cliente1")
        perfil, creado = PerfilCliente.objects.update_or_create(
            usuario=cliente,
            defaults={"telefono": "123456789"},
        )
        self.avisar(creado, f"perfil de {perfil.usuario.username}")

        direccion, creado = Direccion.objects.update_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={
                "direccion": "Direccion de demostracion",
                "referencia": "",
            },
        )
        self.avisar(creado, f"direccion {direccion.alias} de {cliente.username}")

        categorias = {}
        for nombre in ("Cafe", "Pasteleria"):
            categoria, creado = Categoria.objects.update_or_create(nombre=nombre)
            categorias[nombre] = categoria
            self.avisar(creado, f"categoria {nombre}")

        productos = {}
        for nombre, categoria, precio, disponible in PRODUCTOS_DEMO:
            producto, creado = Producto.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categorias[categoria],
                    "precio": Decimal(precio),
                    "disponible": disponible,
                },
            )
            productos[nombre] = producto
            self.avisar(creado, f"producto {nombre}")

        for nombre in ("Cappuccino", "Latte"):
            for tipo, opcion_nombre, recargo in OPCIONES_DEMO:
                opcion, creado = OpcionProducto.objects.update_or_create(
                    producto=productos[nombre],
                    tipo=tipo,
                    nombre=opcion_nombre,
                    defaults={"recargo": Decimal(recargo)},
                )
                self.avisar(creado, f"opcion {opcion.nombre} de {nombre}")

        hoy = timezone.localdate()
        codigo, creado = CodigoDescuento.objects.update_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
                "solo_primer_pedido": True,
                "activo": True,
            },
        )
        self.avisar(creado, f"codigo {codigo.codigo}")
