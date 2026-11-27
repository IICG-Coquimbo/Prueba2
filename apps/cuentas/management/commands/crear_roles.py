from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cuentas.models import Direccion, PerfilCliente
from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.promociones.models import CodigoDescuento

APPS_MODELO = ["cuentas", "catalogo", "promociones", "pedidos", "pagos", "entregas"]

ROLES = {
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
    "Administrador": [],
    "Dueno": [
        "pedidos.ver_reportes",
        "pedidos.view_pedido",
        "entregas.view_entrega",
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


class Command(BaseCommand):
    help = "Crea grupos y permisos. Con --demo crea usuarios y datos de prueba."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea usuarios y datos de demostracion.")

    def _permisos(self, codenames):
        perms = []
        for codename in codenames:
            app, accion_modelo = codename.split(".", 1)
            accion, modelo = accion_modelo.split("_", 1)
            try:
                perms.append(Permission.objects.get(codename=accion + "_" + modelo, content_type__app_label=app))
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Permiso no encontrado: {codename}"))
        return perms

    def _grupos(self):
        for nombre, codenames in ROLES.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(f"Grupo creado: {nombre}")
            if nombre == "Administrador":
                todos = []
                for app in APPS_MODELO:
                    todos.extend(Permission.objects.filter(content_type__app_label=app))
                grupo.permissions.set(todos)
            else:
                grupo.permissions.set(self._permisos(codenames))
            grupo.save()

    def _demo(self):
        # Grupos
        self._grupos()

        # Usuarios
        for username, rol, es_staff in USUARIOS_DEMO:
            user, creado = User.objects.get_or_create(username=username)
            if creado or not user.has_usable_password():
                user.set_password("clave1234")
                user.is_staff = es_staff
                user.save()
                grupo = Group.objects.get(name=rol)
                user.groups.clear()
                user.groups.add(grupo)
                self.stdout.write(f"Usuario creado: {username} ({rol})")

        # cliente1 con perfil y direccion Casa
        cliente = User.objects.get(username="cliente1")
        PerfilCliente.objects.get_or_create(usuario=cliente, defaults={"telefono": "900000000"})
        Direccion.objects.get_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={"direccion": "Casa Matriz 123", "referencia": "Casa"},
        )

        # Categorias
        cat_cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
        cat_pasteleria, _ = Categoria.objects.get_or_create(nombre="Pasteleria")

        # Productos
        prods = {
            "Espresso": (cat_cafe, 1800, True),
            "Cappuccino": (cat_cafe, 2800, True),
            "Latte": (cat_cafe, 3000, True),
            "Croissant": (cat_pasteleria, 2200, True),
            "Torta de chocolate": (cat_pasteleria, 3200, False),
        }
        for nombre, (categoria, precio, disponible) in prods.items():
            Producto.objects.get_or_create(
                nombre=nombre,
                defaults={"categoria": categoria, "precio": precio, "disponible": disponible, "descripcion": ""},
            )

        # Opciones para Cappuccino y Latte
        opciones = {
            "Cappuccino": [
                ("tamano", "Pequeno", 0),
                ("tamano", "Mediano", 500),
                ("tamano", "Grande", 900),
                ("leche", "Entera", 0),
                ("leche", "Avena", 600),
                ("azucar", "Sin azucar", 0),
                ("azucar", "Con azucar", 0),
            ],
            "Latte": [
                ("tamano", "Pequeno", 0),
                ("tamano", "Mediano", 500),
                ("tamano", "Grande", 900),
                ("leche", "Entera", 0),
                ("leche", "Avena", 600),
                ("azucar", "Sin azucar", 0),
                ("azucar", "Con azucar", 0),
            ],
        }
        for nombre_producto, lista in opciones.items():
            producto = Producto.objects.get(nombre=nombre_producto)
            for tipo, nombre_op, recargo in lista:
                OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre_op,
                    defaults={"recargo": recargo},
                )

        # Codigo BIENVENIDA10
        hoy = timezone.localdate()
        hasta = hoy + timedelta(days=60)
        CodigoDescuento.objects.get_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hasta,
                "solo_primer_pedido": True,
                "activo": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Datos de demostracion creados."))

    def handle(self, *args, **options):
        self._grupos()
        self.stdout.write(self.style.SUCCESS("Grupos y permisos creados/actualizados."))
        if options["demo"]:
            self._demo()
