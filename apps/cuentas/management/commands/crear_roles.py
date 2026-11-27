from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

APPS_ADMIN = ["cuentas", "catalogo", "promociones", "pedidos", "pagos", "entregas"]

GRUPOS = {
    "Cliente": {
        "catalogo": ["view_producto", "view_categoria"],
        "pedidos": [
            "view_pedido",
            "add_pedido",
            "change_pedido",
            "view_itempedido",
            "add_itempedido",
            "change_itempedido",
            "delete_itempedido",
        ],
        "cuentas": ["view_direccion", "add_direccion", "change_direccion", "delete_direccion"],
    },
    "Barista": {
        "pedidos": ["view_pedido", "preparar_pedido"],
        "catalogo": ["view_producto"],
    },
    "Repartidor": {
        "pedidos": ["view_pedido", "despachar_pedido"],
        "entregas": ["view_entrega", "add_entrega", "change_entrega"],
    },
    "Dueno": {
        "pedidos": ["ver_reportes", "view_pedido"],
        "entregas": ["view_entrega"],
    },
}

USUARIOS_DEMO = [
    ("admin1", "Administrador"),
    ("barista1", "Barista"),
    ("repartidor1", "Repartidor"),
    ("repartidor2", "Repartidor"),
    ("dueno1", "Dueno"),
    ("cliente1", "Cliente"),
]

PRODUCTOS_DEMO = [
    ("Espresso", "Cafe", Decimal("1800"), True),
    ("Cappuccino", "Cafe", Decimal("2800"), True),
    ("Latte", "Cafe", Decimal("3000"), True),
    ("Croissant", "Pasteleria", Decimal("2200"), True),
    ("Torta de chocolate", "Pasteleria", Decimal("3200"), False),
]

OPCIONES_DEMO = [
    ("tamano", "Pequeno", Decimal("0")),
    ("tamano", "Mediano", Decimal("500")),
    ("tamano", "Grande", Decimal("900")),
    ("leche", "Entera", Decimal("0")),
    ("leche", "Avena", Decimal("600")),
    ("azucar", "Sin azucar", Decimal("0")),
    ("azucar", "Con azucar", Decimal("0")),
]


class Command(BaseCommand):
    help = "Crea los grupos, permisos y datos de demostracion de Cafe Rincon."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea usuarios y datos de demostracion.")

    def handle(self, *args, **options):
        for nombre, especificacion in list(GRUPOS.items()) + [("Administrador", None)]:
            grupo, creado = Group.objects.get_or_create(name=nombre)
            permisos = self.obtener_permisos(especificacion)
            grupo.permissions.set(permisos)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {nombre}"))
            else:
                self.stdout.write(f"Grupo actualizado: {nombre}")

        if options["demo"]:
            self.crear_demo()

    def obtener_permisos(self, especificacion):
        if especificacion is None:
            return list(Permission.objects.filter(content_type__app_label__in=APPS_ADMIN))
        permisos = []
        for app_label, codenames in especificacion.items():
            encontrados = list(
                Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename__in=codenames,
                )
            )
            if len(encontrados) != len(codenames):
                raise CommandError(f"Faltan permisos en {app_label}: {codenames}")
            permisos.extend(encontrados)
        return permisos

    def crear_demo(self):
        for username, nombre_grupo in USUARIOS_DEMO:
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={"first_name": username, "email": f"{username}@cafedemo.cl"},
            )
            if creado:
                usuario.set_password("clave1234")
                usuario.save()
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username}"))
            usuario.groups.add(Group.objects.get(name=nombre_grupo))
            if username == "admin1" and not usuario.is_staff:
                usuario.is_staff = True
                usuario.save(update_fields=["is_staff"])

        cliente = User.objects.get(username="cliente1")
        perfil, creado = PerfilCliente.objects.get_or_create(
            usuario=cliente,
            defaults={"telefono": "+56 9 1111 1111"},
        )
        if creado:
            self.stdout.write(self.style.SUCCESS(f"Perfil creado: {perfil}"))
        direccion, creado = Direccion.objects.get_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={
                "direccion": "Calle Principal 123",
                "referencia": "Porton marron",
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS(f"Direccion creada: {direccion}"))

        categorias = {}
        for nombre in ("Cafe", "Pasteleria"):
            categoria, _creado = Categoria.objects.get_or_create(nombre=nombre)
            categorias[nombre] = categoria

        productos = {}
        for nombre, categoria, precio, disponible in PRODUCTOS_DEMO:
            producto, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categorias[categoria],
                    "precio": precio,
                    "disponible": disponible,
                },
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Producto creado: {producto}"))
            productos[nombre] = producto

        for nombre_producto in ("Cappuccino", "Latte"):
            producto = productos[nombre_producto]
            for tipo, nombre, recargo in OPCIONES_DEMO:
                opcion, creado = OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": recargo},
                )
                if creado:
                    self.stdout.write(self.style.SUCCESS(f"Opcion creada: {opcion}"))

        hoy = timezone.localdate()
        codigo, creado = CodigoDescuento.objects.get_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
                "solo_primer_pedido": True,
                "activo": True,
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS(f"Codigo creado: {codigo}"))
