from django.contrib import admin

from .models import HistorialEstado, ItemPedido, Pedido


admin.site.register(Pedido)
admin.site.register(ItemPedido)
admin.site.register(HistorialEstado)
