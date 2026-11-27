from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.cuentas.models import PerfilCliente, Direccion
from apps.catalogo.models import Categoria, Producto, OpcionProducto
from apps.promociones.models import CodigoDescuento
from apps.pedidos.models import Pedido, ItemPedido, HistorialEstado
from apps.pagos.models import Pago
from apps.entregas.models import Entrega
from decimal import Decimal
from datetime import date, timedelta


class Command(BaseCommand):
    help = "Crea grupos, permisos y (con --demo) usuarios y datos de prueba segun docs/roles.md"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea usuarios y datos de demostracion")

    def handle(self, *args, **options):
        demo = options["demo"]
        self.stdout.write("Creando grupos y permisos...")

        grupos_permisos = {
            "Cliente": [
                "catalogo.view_producto", "catalogo.view_categoria",
                "pedidos.view_pedido", "pedidos.add_pedido", "pedidos.change_pedido",
                "pedidos.view_itempedido", "pedidos.add_itempedido", "pedidos.change_itempedido", "pedidos.delete_itempedido",
                "cuentas.view_direccion", "cuentas.add_direccion", "cuentas.change_direccion", "cuentas.delete_direccion",
            ],
            "Barista": [
                "pedidos.view_pedido", "pedidos.preparar_pedido", "catalogo.view_producto",
            ],
            "Repartidor": [
                "pedidos.view_pedido", "pedidos.despachar_pedido",
                "entregas.view_entrega", "entregas.add_entrega", "entregas.change_entrega",
            ],
            "Administrador": [],  # Se llena abajo con todos
            "Dueno": [
                "pedidos.ver_reportes", "pedidos.view_pedido", "entregas.view_entrega",
            ],
        }

        apps_modelos = [
            ("cuentas", [PerfilCliente, Direccion]),
            ("catalogo", [Categoria, Producto, OpcionProducto]),
            ("promociones", [CodigoDescuento]),
            ("pedidos", [Pedido, ItemPedido, HistorialEstado]),
            ("pagos", [Pago]),
            ("entregas", [Entrega]),
        ]

        todos_permisos = []
        for app_label, modelos in apps_modelos:
            for modelo in modelos:
                ct = ContentType.objects.get_for_model(modelo)
                perms = Permission.objects.filter(content_type=ct)
                todos_permisos.extend(perms)

        for grupo_nombre, codenames in grupos_permisos.items():
            grupo, created = Group.objects.get_or_create(name=grupo_nombre)
            if created:
                self.stdout.write(f"  Grupo creado: {grupo_nombre}")
            else:
                self.stdout.write(f"  Grupo ya existe: {grupo_nombre}")

            if grupo_nombre == "Administrador":
                grupo.permissions.set(todos_permisos)
                self.stdout.write(f"    Asignados TODOS los permisos ({len(todos_permisos)})")
            else:
                perms = Permission.objects.none()
                for codename in codenames:
                    if "." in codename:
                        app_label, perm_codename = codename.split(".", 1)
                        perms = perms | Permission.objects.filter(content_type__app_label=app_label, codename=perm_codename)
                    else:
                        perms = perms | Permission.objects.filter(codename=codename)
                grupo.permissions.set(perms)
                self.stdout.write(f"    Asignados {perms.count()} permisos")

        if demo:
            self.stdout.write("\nCreando usuarios de demostracion (clave: clave1234)...")

            usuarios_demo = [
                ("admin1", "Administrador", True),
                ("barista1", "Barista", False),
                ("repartidor1", "Repartidor", False),
                ("repartidor2", "Repartidor", False),
                ("dueno1", "Dueno", False),
                ("cliente1", "Cliente", False),
            ]

            for username, grupo_nombre, is_staff in usuarios_demo:
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": f"{username}@example.com", "is_staff": is_staff}
                )
                if created:
                    user.set_password("clave1234")
                    user.save()
                    self.stdout.write(f"  Usuario creado: {username}")
                else:
                    self.stdout.write(f"  Usuario ya existe: {username}")

                grupo = Group.objects.get(name=grupo_nombre)
                user.groups.add(grupo)
                if is_staff:
                    user.is_staff = True
                    user.save()

                if grupo_nombre == "Cliente":
                    perfil, _ = PerfilCliente.objects.get_or_create(usuario=user, defaults={"telefono": "+56912345678"})
                    if _:
                        self.stdout.write(f"    PerfilCliente creado para {username}")
                    direccion, _ = Direccion.objects.get_or_create(
                        usuario=user, alias="Casa",
                        defaults={"direccion": "Calle Falsa 123", "referencia": "Puerta azul"}
                    )
                    if _:
                        self.stdout.write(f"    Direccion 'Casa' creada para {username}")

            self.stdout.write("\nCreando datos de demostracion...")

            cat_cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
            cat_pasteleria, _ = Categoria.objects.get_or_create(nombre="Pasteleria")

            productos_demo = [
                ("Espresso", cat_cafe, Decimal("1800"), True, ""),
                ("Cappuccino", cat_cafe, Decimal("2800"), True, ""),
                ("Latte", cat_cafe, Decimal("3000"), True, ""),
                ("Croissant", cat_pasteleria, Decimal("2200"), True, ""),
                ("Torta de chocolate", cat_pasteleria, Decimal("3200"), False, ""),
            ]

            for nombre, cat, precio, disp, img in productos_demo:
                prod, created = Producto.objects.get_or_create(
                    nombre=nombre,
                    defaults={"categoria": cat, "precio": precio, "disponible": disp, "imagen_url": img}
                )
                if created:
                    self.stdout.write(f"  Producto creado: {nombre}")

            cappuccino = Producto.objects.get(nombre="Cappuccino")
            latte = Producto.objects.get(nombre="Latte")

            opciones_demo = [
                (cappuccino, "tamano", "Pequeno", Decimal("0")),
                (cappuccino, "tamano", "Mediano", Decimal("500")),
                (cappuccino, "tamano", "Grande", Decimal("900")),
                (cappuccino, "leche", "Entera", Decimal("0")),
                (cappuccino, "leche", "Avena", Decimal("600")),
                (cappuccino, "azucar", "Sin azucar", Decimal("0")),
                (cappuccino, "azucar", "Con azucar", Decimal("0")),
                (latte, "tamano", "Pequeno", Decimal("0")),
                (latte, "tamano", "Mediano", Decimal("500")),
                (latte, "tamano", "Grande", Decimal("900")),
                (latte, "leche", "Entera", Decimal("0")),
                (latte, "leche", "Avena", Decimal("600")),
                (latte, "azucar", "Sin azucar", Decimal("0")),
                (latte, "azucar", "Con azucar", Decimal("0")),
            ]

            for prod, tipo, nombre, recargo in opciones_demo:
                op, created = OpcionProducto.objects.get_or_create(
                    producto=prod, tipo=tipo, nombre=nombre,
                    defaults={"recargo": recargo}
                )
                if created:
                    self.stdout.write(f"  Opcion creada: {prod.nombre} - {nombre}")

            hoy = date.today()
            codigo, created = CodigoDescuento.objects.get_or_create(
                codigo="BIENVENIDA10",
                defaults={
                    "porcentaje": 10,
                    "vigente_desde": hoy,
                    "vigente_hasta": hoy + timedelta(days=60),
                    "solo_primer_pedido": True,
                    "activo": True
                }
            )
            if created:
                self.stdout.write(f"  Codigo creado: BIENVENIDA10 (10%, solo primer pedido, 60 dias)")

        self.stdout.write(self.style.SUCCESS("\nComando completado exitosamente."))