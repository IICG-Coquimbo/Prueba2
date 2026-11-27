from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento

CLAVE_DEMO = "clave1234"
APPS_ADMIN = [
    "cuentas",
    "catalogo",
    "promociones",
    "pedidos",
    "pagos",
    "entregas",
]
PERMISOS_CLIENTE = [
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
]
PERMISOS_BARISTA = [
    "pedidos.view_pedido",
    "pedidos.preparar_pedido",
    "catalogo.view_producto",
]
PERMISOS_REPARTIDOR = [
    "pedidos.view_pedido",
    "pedidos.despachar_pedido",
    "entregas.view_entrega",
    "entregas.add_entrega",
    "entregas.change_entrega",
]
PERMISOS_DUENO = [
    "pedidos.ver_reportes",
    "pedidos.view_pedido",
    "entregas.view_entrega",
]


class Command(BaseCommand):
    help = "Crea o actualiza los grupos, permisos y datos de demostracion"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true")

    def handle(self, *args, **options):
        self.crear_grupos()
        if options["demo"]:
            self.crear_datos_demo()

    def permisos(self, nombres):
        consulta = Q()
        for nombre in nombres:
            app_label, codename = nombre.split(".")
            consulta |= Q(content_type__app_label=app_label, codename=codename)
        return Permission.objects.filter(consulta)

    def registrar(self, etiqueta, objeto, creado):
        accion = "creado" if creado else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"{etiqueta} {accion}: {objeto}"))

    def crear_grupo(self, nombre, nombres_permisos):
        grupo, creado = Group.objects.get_or_create(name=nombre)
        permisos = self.permisos(nombres_permisos)
        grupo.permissions.set(permisos)
        self.registrar(f"Grupo {nombre} ({permisos.count()} permisos)", grupo, creado)
        return grupo

    def crear_grupo_admin(self):
        grupo, creado = Group.objects.get_or_create(name="Administrador")
        permisos = Permission.objects.filter(
            content_type__app_label__in=APPS_ADMIN
        )
        grupo.permissions.set(permisos)
        self.registrar(
            f"Grupo Administrador ({permisos.count()} permisos)", grupo, creado
        )

    def crear_grupos(self):
        self.crear_grupo("Cliente", PERMISOS_CLIENTE)
        self.crear_grupo("Barista", PERMISOS_BARISTA)
        self.crear_grupo("Repartidor", PERMISOS_REPARTIDOR)
        self.crear_grupo_admin()
        self.crear_grupo("Dueno", PERMISOS_DUENO)

    def crear_usuario(self, username, nombre_grupo, is_staff=False):
        usuario, creado = User.objects.update_or_create(
            username=username, defaults={"is_staff": is_staff}
        )
        usuario.set_password(CLAVE_DEMO)
        usuario.save(update_fields=["password", "is_staff"])
        usuario.groups.set([Group.objects.get(name=nombre_grupo)])
        self.registrar(f"Usuario {username} (grupo {nombre_grupo})", usuario, creado)
        return usuario

    def crear_datos_demo(self):
        self.crear_usuario("admin1", "Administrador", is_staff=True)
        self.crear_usuario("barista1", "Barista")
        self.crear_usuario("repartidor1", "Repartidor")
        self.crear_usuario("repartidor2", "Repartidor")
        self.crear_usuario("dueno1", "Dueno")
        cliente = self.crear_usuario("cliente1", "Cliente")

        perfil, creado = PerfilCliente.objects.update_or_create(
            usuario=cliente, defaults={"telefono": "912345678"}
        )
        self.registrar(f"PerfilCliente de {cliente.username}", perfil, creado)
        direccion, creado = Direccion.objects.update_or_create(
            usuario=cliente,
            alias="Casa",
            defaults={"direccion": "Av. Principal 123", "referencia": ""},
        )
        self.registrar(f"Direccion de {cliente.username}", direccion, creado)

        cafe, creado = Categoria.objects.get_or_create(nombre="Cafe")
        self.registrar("Categoria", cafe, creado)
        pasteleria, creado = Categoria.objects.get_or_create(nombre="Pasteleria")
        self.registrar("Categoria", pasteleria, creado)

        productos = [
            ("Espresso", cafe, "1800", True),
            ("Cappuccino", cafe, "2800", True),
            ("Latte", cafe, "3000", True),
            ("Croissant", pasteleria, "2200", True),
            ("Torta de chocolate", pasteleria, "3200", False),
        ]
        for nombre, categoria, precio, disponible in productos:
            producto, creado = Producto.objects.update_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categoria,
                    "precio": Decimal(precio),
                    "disponible": disponible,
                },
            )
            self.registrar("Producto", producto, creado)

        opciones = [
            ("tamano", "Pequeno", "0"),
            ("tamano", "Mediano", "500"),
            ("tamano", "Grande", "900"),
            ("leche", "Entera", "0"),
            ("leche", "Avena", "600"),
            ("azucar", "Sin azucar", "0"),
            ("azucar", "Con azucar", "0"),
        ]
        for nombre_producto in ("Cappuccino", "Latte"):
            producto = Producto.objects.get(nombre=nombre_producto)
            for tipo, nombre, recargo in opciones:
                opcion, creado = OpcionProducto.objects.update_or_create(
                    producto=producto,
                    tipo=tipo,
                    nombre=nombre,
                    defaults={"recargo": Decimal(recargo)},
                )
                self.registrar(f"Opcion de {nombre_producto}", opcion, creado)

        hoy = timezone.localdate()
        codigo, creado = CodigoDescuento.objects.update_or_create(
            codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "solo_primer_pedido": True,
                "activo": True,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
            },
        )
        self.registrar("CodigoDescuento", codigo, creado)
