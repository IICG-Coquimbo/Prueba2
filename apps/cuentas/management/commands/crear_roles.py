from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

APPS = ["cuentas", "catalogo", "promociones", "pedidos", "pagos", "entregas"]

ROLES = {
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
    "Administrador": [],
    "Dueno": [
        ("pedidos", "ver_reportes"),
        ("pedidos", "view_pedido"),
        ("entregas", "view_entrega"),
    ],
}

USUARIOS_DEMO = [
    ("admin1", "Administrador"),
    ("barista1", "Barista"),
    ("repartidor1", "Repartidor"),
    ("repartidor2", "Repartidor"),
    ("dueno1", "Dueno"),
    ("cliente1", "Cliente"),
]

DEMO_CATEGORIAS = ("Cafe", "Pasteleria")

DEMO_PRODUCTOS = (
    ("Cafe", "Espresso", "1800", True),
    ("Cafe", "Cappuccino", "2800", True),
    ("Cafe", "Latte", "3000", True),
    ("Pasteleria", "Croissant", "2200", True),
    ("Pasteleria", "Torta de chocolate", "3200", False),
)

DEMO_IMAGENES = {
    "Espresso": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Machine_pouring_coffee_(Unsplash).jpg?width=600",
    "Cappuccino": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Coffee_with_cream_and_sugar_(Unsplash).jpg?width=600",
    "Latte": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Caffe_Latte_at_Pulse_Cafe.jpg?width=600",
    "Croissant": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Croissant-Petr_Kratochvil.jpg?width=600",
    "Torta de chocolate": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Chocolate_Cake_(Unsplash).jpg?width=600",
}

DEMO_OPCIONES = {
    "Cappuccino": (
        ("tamano", "Pequeno", "0"),
        ("tamano", "Mediano", "500"),
        ("tamano", "Grande", "900"),
        ("leche", "Entera", "0"),
        ("leche", "Avena", "600"),
        ("azucar", "Sin azucar", "0"),
        ("azucar", "Con azucar", "0"),
    ),
    "Latte": (
        ("tamano", "Pequeno", "0"),
        ("tamano", "Mediano", "500"),
        ("tamano", "Grande", "900"),
        ("leche", "Entera", "0"),
        ("leche", "Avena", "600"),
        ("azucar", "Sin azucar", "0"),
        ("azucar", "Con azucar", "0"),
    ),
}


class Command(BaseCommand):
    help = "Crea los roles del sistema y, con --demo, los usuarios de demostracion."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true")

    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_usuarios_demo()
            self.crear_datos_demo()

    def crear_grupos(self):
        for nombre, codenames in ROLES.items():
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {nombre}"))
            else:
                self.stdout.write(f"Grupo existente: {nombre}")
            if nombre == "Administrador":
                permisos = Permission.objects.filter(content_type__app_label__in=APPS)
            else:
                permisos = self.permisos_por_codename(codenames)
            antes = grupo.permissions.count()
            grupo.permissions.add(*permisos)
            despues = grupo.permissions.count()
            if despues > antes:
                self.stdout.write(f"  Permisos agregados: {despues - antes}")

    def permisos_por_codename(self, codenames):
        permisos = []
        for app_label, codename in codenames:
            permiso = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permiso is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Permiso aun no disponible: {app_label}.{codename}"
                    )
                )
                continue
            permisos.append(permiso)
        return permisos

    def crear_usuarios_demo(self):
        for username, nombre_grupo in USUARIOS_DEMO:
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": nombre_grupo == "Administrador"},
            )
            if creado:
                usuario.set_password("clave1234")
                usuario.save()
                self.stdout.write(self.style.SUCCESS(f"Usuario creado: {username}"))
            else:
                self.stdout.write(f"Usuario existente: {username}")
            if username == "admin1" and not usuario.is_staff:
                usuario.is_staff = True
                usuario.save(update_fields=["is_staff"])
                self.stdout.write("  admin1 marcado como staff")
            grupo = Group.objects.get(name=nombre_grupo)
            usuario.groups.add(grupo)
            if username == "cliente1":
                _perfil, perfil_creado = PerfilCliente.objects.get_or_create(
                    usuario=usuario, defaults={"telefono": "912345678"}
                )
                if perfil_creado:
                    self.stdout.write("  PerfilCliente creado para cliente1")
                _direccion, direccion_creada = Direccion.objects.get_or_create(
                    usuario=usuario,
                    alias="Casa",
                    defaults={
                        "direccion": "Calle Principal 123",
                        "referencia": "Frente al parque",
                    },
                )
                if direccion_creada:
                    self.stdout.write('  Direccion "Casa" creada para cliente1')

    def crear_datos_demo(self):
        categorias = {}
        for nombre in DEMO_CATEGORIAS:
            categoria, creada = Categoria.objects.get_or_create(nombre=nombre)
            categorias[nombre] = categoria
            if creada:
                self.stdout.write(f"Categoria creada: {nombre}")

        productos = {}
        for categoria_nombre, nombre, precio, disponible in DEMO_PRODUCTOS:
            imagen_url = DEMO_IMAGENES.get(nombre, "")
            producto, creado = Producto.objects.get_or_create(
                categoria=categorias[categoria_nombre],
                nombre=nombre,
                defaults={
                    "precio": Decimal(precio),
                    "disponible": disponible,
                    "imagen_url": imagen_url,
                },
            )
            if not producto.imagen_url and imagen_url:
                producto.imagen_url = imagen_url
                producto.save(update_fields=["imagen_url"])
                self.stdout.write(f"  Foto agregada: {nombre}")
            productos[nombre] = producto
            if creado:
                self.stdout.write(f"Producto creado: {nombre}")

        for nombre_producto, opciones in DEMO_OPCIONES.items():
            for tipo, nombre, recargo in opciones:
                _opcion, creada = OpcionProducto.objects.get_or_create(
                    producto=productos[nombre_producto],
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": Decimal(recargo)},
                )
                if creada:
                    self.stdout.write(f"Opcion creada: {nombre_producto} / {nombre}")

        hoy = timezone.now().date()
        _codigo, creado = CodigoDescuento.objects.get_or_create(
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
            self.stdout.write("Codigo de descuento creado: BIENVENIDA10")
