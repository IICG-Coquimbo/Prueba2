from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Categoria, OpcionProducto, Producto
from apps.cuentas.models import Direccion, PerfilCliente
from apps.promociones.models import CodigoDescuento


APPS_ADMIN = ("cuentas", "catalogo", "promociones", "pedidos", "pagos", "entregas")
PERMISOS_POR_ROL = {
    "Cliente": (
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
    ),
    "Barista": (
        "pedidos.view_pedido",
        "pedidos.preparar_pedido",
        "catalogo.view_producto",
    ),
    "Repartidor": (
        "pedidos.view_pedido",
        "pedidos.despachar_pedido",
        "entregas.view_entrega",
        "entregas.add_entrega",
        "entregas.change_entrega",
    ),
    "Dueno": ("pedidos.ver_reportes", "pedidos.view_pedido", "entregas.view_entrega"),
}
USUARIOS_DEMO = {
    "admin1": "Administrador",
    "barista1": "Barista",
    "repartidor1": "Repartidor",
    "repartidor2": "Repartidor",
    "dueno1": "Dueno",
    "cliente1": "Cliente",
}
OPCIONES_DEMO = (
    (OpcionProducto.Tipo.TAMANO, "Pequeno", 0),
    (OpcionProducto.Tipo.TAMANO, "Mediano", 500),
    (OpcionProducto.Tipo.TAMANO, "Grande", 900),
    (OpcionProducto.Tipo.LECHE, "Entera", 0),
    (OpcionProducto.Tipo.LECHE, "Avena", 600),
    (OpcionProducto.Tipo.AZUCAR, "Sin azucar", 0),
    (OpcionProducto.Tipo.AZUCAR, "Con azucar", 0),
)


class Command(BaseCommand):
    help = "Configura los roles de Cafe Rincon y, opcionalmente, carga la demostración."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea los datos del curso.")

    def handle(self, *args, **options):
        creados = []
        with transaction.atomic():
            grupos = self.crear_grupos(creados)
            if options["demo"]:
                self.crear_demo(grupos, creados)

        for objeto in creados:
            self.stdout.write(f"Creado: {objeto}")
        self.stdout.write(self.style.SUCCESS("Permisos de los roles configurados."))

    def obtener_o_crear(self, modelo, creados, **kwargs):
        objeto, creado = modelo.objects.get_or_create(**kwargs)
        if creado:
            creados.append(f"{modelo.__name__}: {objeto}")
        return objeto

    def crear_grupos(self, creados):
        permisos_admin = list(
            Permission.objects.filter(content_type__app_label__in=APPS_ADMIN)
            .select_related("content_type")
        )
        disponibles = {
            f"{permiso.content_type.app_label}.{permiso.codename}": permiso
            for permiso in permisos_admin
        }
        requeridos = {permiso for permisos in PERMISOS_POR_ROL.values() for permiso in permisos}
        faltantes = requeridos - disponibles.keys()
        if faltantes:
            raise CommandError(
                f"Faltan permisos ({', '.join(sorted(faltantes))}). Ejecuta migrate primero."
            )

        grupos = {}
        for rol, permisos in PERMISOS_POR_ROL.items():
            grupo = self.obtener_o_crear(Group, creados, name=rol)
            grupo.permissions.set(disponibles[permiso] for permiso in permisos)
            grupos[rol] = grupo

        administrador = self.obtener_o_crear(Group, creados, name="Administrador")
        administrador.permissions.set(permisos_admin)
        grupos["Administrador"] = administrador
        return grupos

    def crear_demo(self, grupos, creados):
        for username, rol in USUARIOS_DEMO.items():
            usuario = self.obtener_o_crear(
                User, creados, username=username,
                defaults={"password": lambda: make_password("clave1234")},
            )
            usuario.groups.add(grupos[rol])
            if rol == "Administrador" and not usuario.is_staff:
                usuario.is_staff = True
                usuario.save(update_fields=["is_staff"])
            if rol == "Cliente":
                self.obtener_o_crear(
                    PerfilCliente, creados, usuario=usuario,
                    defaults={"telefono": "000000000"},
                )
                self.obtener_o_crear(
                    Direccion, creados, usuario=usuario, alias="Casa",
                    defaults={"direccion": "Calle de Ejemplo 123"},
                )

        cafe = self.obtener_o_crear(Categoria, creados, nombre="Cafe")
        pasteleria = self.obtener_o_crear(Categoria, creados, nombre="Pasteleria")
        for categoria, nombre, precio, disponible in (
            (cafe, "Espresso", 1800, True),
            (cafe, "Cappuccino", 2800, True),
            (cafe, "Latte", 3000, True),
            (pasteleria, "Croissant", 2200, True),
            (pasteleria, "Torta de chocolate", 3200, False),
        ):
            producto = self.obtener_o_crear(
                Producto, creados, categoria=categoria, nombre=nombre,
                defaults={"precio": precio, "disponible": disponible},
            )
            if nombre in ("Cappuccino", "Latte"):
                for tipo, opcion, recargo in OPCIONES_DEMO:
                    self.obtener_o_crear(
                        OpcionProducto, creados, producto=producto, tipo=tipo,
                        nombre=opcion, defaults={"recargo": recargo},
                    )

        hoy = timezone.localdate()
        self.obtener_o_crear(
            CodigoDescuento, creados, codigo="BIENVENIDA10",
            defaults={
                "porcentaje": 10,
                "vigente_desde": hoy,
                "vigente_hasta": hoy + timedelta(days=60),
                "solo_primer_pedido": True,
                "activo": True,
            },
        )
