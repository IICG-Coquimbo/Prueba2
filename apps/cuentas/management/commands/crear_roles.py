from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto, TipoOpcion
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento


class Command(BaseCommand):
    help = "Crea los grupos, permisos y datos de demostración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Crea también los usuarios y datos de demostración.",
        )

    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_usuarios_demo()
            self.crear_datos_demo()

    def obtener_permiso(self, app_label, codename):
        return Permission.objects.get(
            codename=codename,
            content_type__app_label=app_label,
        )

    def crear_grupos(self):
        roles = [
            (
                "Cliente",
                [
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
            ),
            (
                "Barista",
                [
                    ("pedidos", "view_pedido"),
                    ("pedidos", "preparar_pedido"),
                    ("catalogo", "view_producto"),
                ],
            ),
            (
                "Repartidor",
                [
                    ("pedidos", "view_pedido"),
                    ("pedidos", "despachar_pedido"),
                    ("entregas", "view_entrega"),
                    ("entregas", "add_entrega"),
                    ("entregas", "change_entrega"),
                ],
            ),
            ("Administrador", []),
            (
                "Dueno",
                [
                    ("pedidos", "ver_reportes"),
                    ("pedidos", "view_pedido"),
                    ("entregas", "view_entrega"),
                ],
            ),
        ]

        for nombre, codigos in roles:
            if nombre == "Administrador":
                permisos = list(
                    Permission.objects.filter(
                        content_type__app_label__in=[
                            "cuentas",
                            "catalogo",
                            "promociones",
                            "pedidos",
                            "pagos",
                            "entregas",
                        ]
                    )
                )
            else:
                permisos = [
                    self.obtener_permiso(app_label, codename)
                    for app_label, codename in codigos
                ]

            grupo, creado = Group.objects.get_or_create(name=nombre)
            grupo.permissions.set(permisos)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {nombre}"))
            else:
                self.stdout.write(f"Grupo existente: {nombre}")
            self.stdout.write(f"Permisos asignados a {nombre}: {len(permisos)}")

    def crear_usuarios_demo(self):
        usuarios = [
            ("admin1", "Administrador", True),
            ("barista1", "Barista", False),
            ("repartidor1", "Repartidor", False),
            ("repartidor2", "Repartidor", False),
            ("dueno1", "Dueno", False),
            ("cliente1", "Cliente", False),
        ]

        for username, rol, es_staff in usuarios:
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": es_staff},
            )
            usuario.is_staff = es_staff
            usuario.set_password("clave1234")
            usuario.save()
            usuario.groups.set([Group.objects.get(name=rol)])
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username}"))
            else:
                self.stdout.write(f"Usuario actualizado: {username}")

        cliente = User.objects.get(username="cliente1")
        _, creado = PerfilCliente.objects.update_or_create(
            usuario=cliente,
            defaults={"telefono": "912345678"},
        )
        if creado:
            self.stdout.write(self.style.SUCCESS("Perfil de cliente1 creado"))
        else:
            self.stdout.write("Perfil de cliente1 actualizado")

        _, creado = Direccion.objects.update_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={
                "direccion": "Av. Principal 123",
                "referencia": "Frente al parque",
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS("Dirección Casa creada"))
        else:
            self.stdout.write("Dirección Casa actualizada")

    def crear_datos_demo(self):
        cafe, creado = Categoria.objects.get_or_create(nombre="Cafe")
        if creado:
            self.stdout.write(self.style.SUCCESS("Categoría creada: Cafe"))

        pasteleria, creado = Categoria.objects.get_or_create(nombre="Pasteleria")
        if creado:
            self.stdout.write(self.style.SUCCESS("Categoría creada: Pasteleria"))

        productos = [
            (cafe, "Espresso", Decimal("1800"), True),
            (cafe, "Cappuccino", Decimal("2800"), True),
            (cafe, "Latte", Decimal("3000"), True),
            (pasteleria, "Croissant", Decimal("2200"), True),
            (pasteleria, "Torta de chocolate", Decimal("3200"), False),
        ]
        for categoria, nombre, precio, disponible in productos:
            _, creado = Producto.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "precio": precio,
                    "disponible": disponible,
                },
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Producto creado: {nombre}"))
            else:
                self.stdout.write(f"Producto actualizado: {nombre}")

        opciones = [
            (TipoOpcion.TAMANO, "Pequeno", Decimal("0")),
            (TipoOpcion.TAMANO, "Mediano", Decimal("500")),
            (TipoOpcion.TAMANO, "Grande", Decimal("900")),
            (TipoOpcion.LECHE, "Entera", Decimal("0")),
            (TipoOpcion.LECHE, "Avena", Decimal("600")),
            (TipoOpcion.AZUCAR, "Sin azucar", Decimal("0")),
            (TipoOpcion.AZUCAR, "Con azucar", Decimal("0")),
        ]
        for producto in Producto.objects.filter(nombre__in=["Cappuccino", "Latte"]):
            for tipo, nombre, recargo in opciones:
                _, creado = OpcionProducto.objects.update_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": recargo},
                )
                if creado:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Opción creada: {producto.nombre} - {nombre}"
                        )
                    )

        hoy = timezone.now().date()
        _, creado = CodigoDescuento.objects.update_or_create(
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
            self.stdout.write(self.style.SUCCESS("Código de descuento creado: BIENVENIDA10"))
        else:
            self.stdout.write("Código de descuento actualizado: BIENVENIDA10")
