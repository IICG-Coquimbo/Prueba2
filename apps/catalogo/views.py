from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.pedidos.forms import AgregarAlCarritoForm
from apps.pedidos.servicios import agregar_item, obtener_carrito

from .models import Producto


class ProductoListView(PermissionRequiredMixin, ListView):
    permission_required = 'catalogo.view_producto'
    model = Producto
    template_name = 'catalogo/producto_list.html'
    context_object_name = 'productos'

    def get_queryset(self):
        queryset = Producto.objects.all()
        if not self.request.user.has_perm('catalogo.change_producto'):
            queryset = queryset.filter(disponible=True)
        return queryset.order_by('nombre')


class ProductoDetailView(PermissionRequiredMixin, DetailView):
    permission_required = 'catalogo.view_producto'
    model = Producto
    template_name = 'catalogo/producto_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AgregarAlCarritoForm(producto=self.object)
        return context


class ProductoAgregarView(PermissionRequiredMixin, FormView):
    permission_required = 'pedidos.add_pedido'
    form_class = AgregarAlCarritoForm
    template_name = 'accion_form.html'
    success_url = reverse_lazy('pedidos:carrito_detail')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.producto = get_object_or_404(Producto, pk=self.kwargs['pk'])
        kwargs['producto'] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Agregar al carrito'
        context['producto'] = self.producto
        return context

    def form_valid(self, form):
        producto = self.producto
        pedido = obtener_carrito(self.request.user)
        try:
            agregar_item(
                pedido,
                producto,
                form.cleaned_data['cantidad'],
                form.opciones_seleccionadas(),
            )
        except ValidationError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, 'Producto agregado al carrito.')
        return super().form_valid(form)
