from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Direccion, PerfilCliente

User = get_user_model()


class PerfilClienteInline(admin.StackedInline):
    model = PerfilCliente
    can_delete = False
    max_num = 1
    verbose_name_plural = "Perfil"


class DireccionInline(admin.TabularInline):
    model = Direccion
    extra = 1


class UsuarioAdmin(UserAdmin):
    inlines = [PerfilClienteInline, DireccionInline]


admin.site.unregister(User)
admin.site.register(User, UsuarioAdmin)


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ["usuario", "telefono"]
    search_fields = ["usuario__username", "telefono"]


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ["alias", "direccion", "usuario"]
    list_filter = ["usuario"]
    search_fields = ["alias", "direccion", "usuario__username"]
