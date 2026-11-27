from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()

APPS_MODELS = {
    "cuentas": ["perfilcliente", "direccion"],
    "catalogo": ["categoria", "producto", "opcionproducto"],
    "promociones": ["codigodescuento"],
    "pedidos": ["pedido", "itempedido", "historialestado"],
    "pagos": ["pago"],
    "entregas": ["entrega"],
}

ROLES_PERMISOS = {
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
    "Administrador": [],  # se llena con todos los permisos
    "Dueno": [
        "pedidos.ver_reportes",
        "pedidos.view_pedido",
        "entregas.view_entrega",
    ],
}

DEMO_USERS = {
    "admin1": ("Administrador", True),
    "barista1": ("Barista", False),
    "repartidor1": ("Repartidor", False),
    "repartidor2": ("Repartidor", False),
    "dueno1": ("Dueno", False),
    "cliente1": ("Cliente", False),
}

DEMO_DATA_NOTE = "Datos de demostracion: categorias, productos, opciones y codigo BIENVENIDA10 se crean desde el admin."


class Command(BaseCommand):
    help = "Crea grupos, permisos y (con --demo) usuarios y datos de demostracion segun docs/roles.md."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Tambien crea usuarios y datos de demostracion.")

    def handle(self, *args, **options):
        demo = options["demo"]

        # Crear grupos y asignar permisos
        todos_permisos = []
        for app_label, modelos in APPS_MODELS.items():
            for modelo in modelos:
                ct = ContentType.objects.filter(app_label=app_label, model=modelo).first()
                if ct:
                    perms = Permission.objects.filter(content_type=ct)
                    for p in perms:
                        todos_permisos.append(p)

        for nombre_rol, permisos_rol in ROLES_PERMISOS.items():
            grupo, creado = Group.objects.get_or_create(name=nombre_rol)
            if nombre_rol == "Administrador":
                grupo.permissions.set(todos_permisos)
                accion = "creado" if creado else "actualizado (todos los permisos)"
            else:
                perms_objs = []
                for cod in permisos_rol:
                    app_label, resto = cod.split(".", 1)
                    accion_modelo = resto.split("_", 1)
                    accion = accion_modelo[0]
                    modelo = accion_modelo[1]
                    ct = ContentType.objects.filter(app_label=app_label, model=modelo).first()
                    if ct:
                        p = Permission.objects.filter(content_type=ct, codename=f"{accion}_{modelo}").first()
                        if p:
                            perms_objs.append(p)
                grupo.permissions.set(perms_objs)
                accion = "creado" if creado else "actualizado"
            self.stdout.write(f"Grupo '{nombre_rol}' {accion}.")

        if demo:
            # Crear usuarios de demostracion
            for username, (rol, is_staff) in DEMO_USERS.items():
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(username=username, password="clave1234")
                    user.is_staff = is_staff
                    user.save()
                    grupo = Group.objects.get(name=rol)
                    user.groups.add(grupo)
                    self.stdout.write(f"Usuario '{username}' creado (rol: {rol}, staff: {is_staff}).")

                    if username == "cliente1":
                        from apps.cuentas.models import PerfilCliente, Direccion
                        perfil, _ = PerfilCliente.objects.get_or_create(usuario=user, defaults={"telefono": ""})
                        direccion, _ = Direccion.objects.get_or_create(
                            usuario=user, alias="Casa",
                            defaults={"direccion": "Calle Falsa 123", "referencia": ""},
                        )
                        self.stdout.write(f"  PerfilCliente y direccion 'Casa' creados para {username}.")
                else:
                    self.stdout.write(f"Usuario '{username}' ya existe, se omite.")

        self.stdout.write(self.style.SUCCESS("Comando crear_roles finalizado."))
