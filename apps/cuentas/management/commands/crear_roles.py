from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cuentas.models import Direccion, PerfilCliente


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

APPS_ADMIN = ["cuentas", "catalogo", "promociones", "pedidos", "pagos", "entregas"]


class Command(BaseCommand):
    help = "Crea roles, permisos, usuarios y datos de demostración."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea usuarios y datos de demostración")

    @transaction.atomic
    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_demo()
        self.stdout.write(self.style.SUCCESS("Roles creados/actualizados correctamente."))

    def obtener_permiso(self, permiso_str):
        app_label, codename = permiso_str.split(".", 1)
        try:
            return Permission.objects.get(content_type__app_label=app_label, codename=codename)
        except Permission.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"Permiso no encontrado: {permiso_str}"))
            return None

    def crear_grupos(self):
        for nombre, permisos_str in PERMISOS_POR_GRUPO.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            permisos = []
            for permiso_str in permisos_str:
                permiso = self.obtener_permiso(permiso_str)
                if permiso:
                    permisos.append(permiso)
            grupo.permissions.set(permisos)
            self.stdout.write(f"Grupo {'creado' if creado else 'actualizado'}: {nombre}")

        admin_group, creado = Group.objects.get_or_create(name="Administrador")
        permisos_admin = Permission.objects.filter(content_type__app_label__in=APPS_ADMIN)
        admin_group.permissions.set(permisos_admin)
        self.stdout.write(f"Grupo {'creado' if creado else 'actualizado'}: Administrador ({permisos_admin.count()} permisos)")

    def crear_demo(self):
        from datetime import timedelta
        from decimal import Decimal

        from django.utils import timezone

        from apps.catalogo.models import Categoria, OpcionProducto, Producto
        from apps.promociones.models import CodigoDescuento

        usuarios_demo = [
            ("admin1", "Administrador", "Admin Uno", "", True),
            ("barista1", "Barista", "Barista Uno", "", False),
            ("repartidor1", "Repartidor", "Repartidor Uno", "", False),
            ("repartidor2", "Repartidor", "Repartidor Dos", "", False),
            ("dueno1", "Dueno", "Dueno Uno", "", False),
            ("cliente1", "Cliente", "Cliente Uno", "123456789", False),
        ]

        for username, rol, nombre, telefono, es_staff in usuarios_demo:
            user, creado = User.objects.get_or_create(
                username=username,
                defaults={"first_name": nombre, "email": f"{username}@caferincon.cl", "is_staff": es_staff},
            )
            if creado:
                user.set_password("clave1234")
            user.first_name = nombre
            user.is_staff = es_staff
            user.email = f"{username}@caferincon.cl"
            user.save()
            grupo = Group.objects.get(name=rol)
            user.groups.set([grupo])
            if rol == "Cliente":
                perfil, _ = PerfilCliente.objects.get_or_create(usuario=user, defaults={"telefono": telefono})
                if telefono and perfil.telefono != telefono:
                    perfil.telefono = telefono
                    perfil.save(update_fields=["telefono"])
                Direccion.objects.get_or_create(
                    usuario=user,
                    alias="Casa",
                    defaults={"direccion": "Av. Principal 123", "referencia": "Casa azul"},
                )
            self.stdout.write(f"Usuario {'creado' if creado else 'actualizado'}: {username}")

        cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
        pasteleria, _ = Categoria.objects.get_or_create(nombre="Pasteleria")

        productos = [
            (cafe, "Espresso", "", Decimal("1800"), "", True),
            (cafe, "Cappuccino", "", Decimal("2800"), "", True),
            (cafe, "Latte", "", Decimal("3000"), "", True),
            (pasteleria, "Croissant", "", Decimal("2200"), "", True),
            (pasteleria, "Torta de chocolate", "", Decimal("3200"), "", False),
        ]
        objetos_productos = {}
        for categoria, nombre, descripcion, precio, imagen_url, disponible in productos:
            producto, _ = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "descripcion": descripcion,
                    "precio": precio,
                    "imagen_url": imagen_url,
                    "disponible": disponible,
                },
            )
            producto.categoria = categoria
            producto.descripcion = descripcion
            producto.precio = precio
            producto.imagen_url = imagen_url
            producto.disponible = disponible
            producto.save()
            objetos_productos[nombre] = producto

        for nombre_producto in ["Cappuccino", "Latte"]:
            producto = objetos_productos[nombre_producto]
            opciones = [
                ("tamano", "Pequeno", Decimal("0")),
                ("tamano", "Mediano", Decimal("500")),
                ("tamano", "Grande", Decimal("900")),
                ("leche", "Entera", Decimal("0")),
                ("leche", "Avena", Decimal("600")),
                ("azucar", "Sin azucar", Decimal("0")),
                ("azucar", "Con azucar", Decimal("0")),
            ]
            for tipo, nombre, recargo in opciones:
                OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": recargo},
                )

        hoy = timezone.localdate()
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
        self.stdout.write("Datos de demostración creados/actualizados.")
