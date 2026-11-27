"""Comando crear_roles segun docs/reglas_usuarios.md y docs/roles.md.

Crea grupos con permisos, usuarios de demostracion y datos de demo.
Idempotente: se puede repetir sin duplicar.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento


class Command(BaseCommand):
    help = "Crea roles (grupos) con sus permisos y, con --demo, usuarios y datos de demostracion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Tambien crea usuarios de demostracion y datos de demo.",
        )

    def handle(self, *args, **options):
        demo = options["demo"]

        # --- Mapeo de app a modelos para obtener todos los permisos ---
        app_modelos = {
            "cuentas": [PerfilCliente, Direccion],
            "catalogo": [Categoria, Producto, OpcionProducto],
            "promociones": [CodigoDescuento],
            "pedidos": [],
            "pagos": [],
            "entregas": [],
        }

        # Importar modelos de pedidos y pagos y entregas para sus content types
        from apps.pedidos.models import HistorialEstado, ItemPedido, Pedido
        from apps.pagos.models import Pago
        from apps.entregas.models import Entrega

        app_modelos["pedidos"] = [Pedido, ItemPedido, HistorialEstado]
        app_modelos["pagos"] = [Pago]
        app_modelos["entregas"] = [Entrega]

        # Obtener TODOS los permisos de todas las apps con modelos
        todos_los_permisos = []
        for app_label, modelos in app_modelos.items():
            for modelo in modelos:
                ct = ContentType.objects.get_for_model(modelo)
                perms = Permission.objects.filter(content_type=ct)
                todos_los_permisos.extend(perms)

        # Agregar permisos propios de pedidos
        for codename in ["preparar_pedido", "despachar_pedido", "ver_reportes"]:
            try:
                perm = Permission.objects.get(
                    content_type__app_label="pedidos", codename=codename
                )
                todos_los_permisos.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Permiso propio no encontrado: pedidos.{codename}")
                )

        # --- Roles y permisos específicos (según docs/roles.md) ---
        roles_permisos_str = {
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

        def obtener_permiso(codename_str):
            app_label, codename = codename_str.split(".")
            try:
                return Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Permiso no encontrado: {codename_str}")
                )
                return None

        for nombre_rol, permisos_str in roles_permisos_str.items():
            grupo, creado = Group.objects.get_or_create(name=nombre_rol)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {nombre_rol}"))
            else:
                self.stdout.write(f"Grupo ya existe: {nombre_rol}")

            perms_objetos = []
            for ps in permisos_str:
                perm = obtener_permiso(ps)
                if perm:
                    perms_objetos.append(perm)

            grupo.permissions.set(perms_objetos)
            self.stdout.write(
                f"  Asignados {len(perms_objetos)} permisos a {nombre_rol}"
            )

        # Administrador: TODOS los permisos
        grupo_admin, creado = Group.objects.get_or_create(name="Administrador")
        if creado:
            self.stdout.write(self.style.SUCCESS("Grupo creado: Administrador"))
        else:
            self.stdout.write("Grupo ya existe: Administrador")
        grupo_admin.permissions.set(todos_los_permisos)
        self.stdout.write(
            f"  Asignados {len(todos_los_permisos)} permisos a Administrador"
        )

        if not demo:
            self.stdout.write(self.style.SUCCESS("Roles creados (sin --demo)."))
            return

        # --- Usuarios de demostracion ---
        usuarios_demo = [
            ("admin1", "Administrador"),
            ("barista1", "Barista"),
            ("repartidor1", "Repartidor"),
            ("repartidor2", "Repartidor"),
            ("dueno1", "Dueno"),
            ("cliente1", "Cliente"),
        ]

        for username, rol in usuarios_demo:
            user, creado = User.objects.get_or_create(username=username)
            if creado:
                user.set_password("clave1234")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username}"))
            else:
                self.stdout.write(f"Usuario ya existe: {username}")

            grupo = Group.objects.get(name=rol)
            user.groups.add(grupo)

            if rol == "Administrador":
                user.is_staff = True
                user.save()

            if rol == "Cliente":
                PerfilCliente.objects.get_or_create(
                    usuario=user, defaults={"telefono": "00000000"}
                )
                Direccion.objects.get_or_create(
                    usuario=user,
                    alias="Casa",
                    defaults={"direccion": "Direccion de casa", "referencia": ""},
                )

        # --- Datos de demostracion ---
        categoria_cafe, _ = Categoria.objects.get_or_create(nombre="Cafe")
        categoria_pasteleria, _ = Categoria.objects.get_or_create(
            nombre="Pasteleria"
        )

        productos_demo = [
            ("Espresso", categoria_cafe, 1800, True),
            ("Cappuccino", categoria_cafe, 2800, True),
            ("Latte", categoria_cafe, 3000, True),
            ("Croissant", categoria_pasteleria, 2200, True),
            ("Torta de chocolate", categoria_pasteleria, 3200, False),
        ]

        for nombre, categoria, precio, disponible in productos_demo:
            producto, creado = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "precio": precio,
                    "disponible": disponible,
                    "descripcion": "",
                    "imagen_url": "",
                },
            )
            if creado:
                self.stdout.write(
                    self.style.SUCCESS(f"Producto creado: {nombre}")
                )

        # Opciones para Cappuccino y Latte
        for nombre_producto in ("Cappuccino", "Latte"):
            producto = Producto.objects.get(nombre=nombre_producto)
            opciones_demo = [
                ("tamano", "Pequeno", 0),
                ("tamano", "Mediano", 500),
                ("tamano", "Grande", 900),
                ("leche", "Entera", 0),
                ("leche", "Avena", 600),
                ("azucar", "Sin azucar", 0),
                ("azucar", "Con azucar", 0),
            ]
            for tipo, nombre_opcion, recargo in opciones_demo:
                OpcionProducto.objects.get_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre_opcion,
                    defaults={"recargo": recargo},
                )

        # Codigo BIENVENIDA10
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

        self.stdout.write(self.style.SUCCESS("Datos de demostracion creados."))
