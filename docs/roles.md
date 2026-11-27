# Roles y permisos - Cafe Rincon

Permiso = <app>.<accion>_<modelo>. Apps con modelos: cuentas,
catalogo, promociones, pedidos, pagos y entregas.
Registro publico: si (RF-01). Crea el User, su PerfilCliente y lo
agrega al grupo Cliente.

## Roles (grupos)
- Cliente: catalogo.view_producto, catalogo.view_categoria,
  pedidos.view_pedido (solo los suyos), pedidos.add_pedido,
  pedidos.change_pedido, pedidos.view/add/change/delete_itempedido,
  cuentas.view/add/change/delete_direccion (solo las suyas).
  Menu: Inicio, Menu, Carrito, Mis pedidos, Mis direcciones.
- Barista: pedidos.view_pedido, pedidos.preparar_pedido,
  catalogo.view_producto.
  Menu: Inicio, Pedidos.
- Repartidor: pedidos.view_pedido, pedidos.despachar_pedido,
  entregas.view/add/change_entrega.
  Menu: Inicio, Entregas.
- Administrador: TODOS los permisos de cuentas, catalogo,
  promociones, pedidos, pagos y entregas, y marcado como "Es staff".
  Menu: Inicio, Pedidos, Administracion.
- Dueno: pedidos.ver_reportes, pedidos.view_pedido,
  entregas.view_entrega.
  Menu: Inicio, Reportes.

## Permiso por accion
- Agregar al carrito, quitar, aplicar codigo y confirmar:
  pedidos.add_pedido (y el pedido debe ser del usuario)
- Preparar (recibido -> en_preparacion -> listo_despacho):
  pedidos.preparar_pedido
- Despachar (listo_despacho -> en_camino -> entregado):
  pedidos.despachar_pedido
- Reportes: pedidos.ver_reportes
- Productos, categorias, opciones y codigos de descuento (RF-15,
  RF-16): se administran en el admin de Django (Es staff).

## Usuarios de demostracion (clave "clave1234")
- admin1: Administrador
- barista1: Barista
- repartidor1 y repartidor2: Repartidor
- dueno1: Dueno
- cliente1: Cliente, con su PerfilCliente y una direccion "Casa"

## Datos de demostracion
- Categorias: Cafe y Pasteleria.
- Productos: Espresso (1800), Cappuccino (2800), Latte (3000) y
  Croissant (2200), todos disponibles, y Torta de chocolate (3200),
  NO disponible.
- Opciones para Cappuccino y Latte: tamano Pequeno (0), Mediano (500)
  y Grande (900); leche Entera (0) y Avena (600); azucar Sin azucar
  (0) y Con azucar (0).
- Codigo BIENVENIDA10: 10 por ciento, solo primer pedido, vigente
  desde hoy hasta dentro de 60 dias.
- No se crean pedidos: se hacen durante las pruebas.
