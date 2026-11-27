import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

User = get_user_model()

APPS_ADMINISTRADOR = [
    "cuentas",
    "catalogo",
    "promociones",
    "pedidos",
    "pagos",
    "entregas",
]

CLAVE_DEMO = "clave1234"

GRUPOS = {
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


def _permiso(codigo):
    app_label, codename = codigo.split(".", 1)
    try:
        return Permission.objects.get(content_type__app_label=app_label, codename=codename)
    except Permission.DoesNotExist:
        return None


class Command(BaseCommand):
    help = "Crea grupos, permisos, usuarios de prueba y datos de demostracion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Ademas crea usuarios de prueba y datos de demostracion.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        creados = []

        for nombre, permisos in GRUPOS.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                creados.append(f"grupo {nombre}")
            objetos = [p for p in (_permiso(c) for c in permisos) if p is not None]
            grupo.permissions.set(objetos)

        grupo_admin, creado = Group.objects.get_or_create(name="Administrador")
        if creado:
            creados.append("grupo Administrador")
        grupo_admin.permissions.set(
            Permission.objects.filter(content_type__app_label__in=APPS_ADMINISTRADOR)
        )

        if options["demo"]:
            creados.extend(self._crear_demo())

        for linea in creados:
            self.stdout.write(f"Creado: {linea}")
        if not creados:
            self.stdout.write("No hubo cambios.")
        self.stdout.write(self.style.SUCCESS("crear_roles listo."))

    def _crear_demo(self):
        from apps.catalogo.models import Categoria, OpcionProducto, Producto
        from apps.cuentas.models import Direccion, PerfilCliente
        from apps.promociones.models import CodigoDescuento

        creados = []

        def usuario(username, grupo, staff=False):
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            user.is_staff = staff
            user.set_password(CLAVE_DEMO)
            user.save()
            user.groups.set([Group.objects.get(name=grupo)])
            if creado:
                creados.append(f"usuario {username}")
            return user

        usuario("admin1", "Administrador", staff=True)
        usuario("barista1", "Barista")
        usuario("repartidor1", "Repartidor")
        usuario("repartidor2", "Repartidor")
        usuario("dueno1", "Dueno")

        cliente = usuario("cliente1", "Cliente")
        PerfilCliente.objects.get_or_create(
            usuario=cliente,
            defaults={"telefono": "900000000"},
        )
        Direccion.objects.get_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={"direccion": "Calle Ejemplo 123", "referencia": ""},
        )

        cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
        pasteleria, _ = Categoria.objects.get_or_create(nombre="Pasteleria")

        productos = [
            (cafe, "Espresso", "1800", True),
            (cafe, "Cappuccino", "2800", True),
            (cafe, "Latte", "3000", True),
            (pasteleria, "Croissant", "2200", True),
            (pasteleria, "Torta de chocolate", "3200", False),
        ]
        for categoria, nombre, precio, disponible in productos:
            producto, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "precio": precio,
                    "disponible": disponible,
                },
            )
            if not creado:
                producto.categoria = categoria
                producto.precio = precio
                producto.disponible = disponible
                producto.save()
            if creado:
                creados.append(f"producto {nombre}")

        for nombre_producto in ("Cappuccino", "Latte"):
            producto = Producto.objects.get(nombre=nombre_producto)
            opciones = [
                ("tamano", "Pequeno", "0"),
                ("tamano", "Mediano", "500"),
                ("tamano", "Grande", "900"),
                ("leche", "Entera", "0"),
                ("leche", "Avena", "600"),
                ("azucar", "Sin azucar", "0"),
                ("azucar", "Con azucar", "0"),
            ]
            for tipo, nombre, recargo in opciones:
                OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": recargo},
                )

        hoy = datetime.date.today()
        CodigoDescuento.objects.get_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + datetime.timedelta(days=60),
                "solo_primer_pedido": True,
                "activo": True,
            },
        )

        return creados
