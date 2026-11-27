# Identidad del sistema - Cafe Rincon

## Nombre y pie de pagina
- Nombre del sistema: Cafe Rincon
- Pie de pagina, texto de la izquierda: Cafe Rincon

## Colores
- --color-primario: #5D4037   (cafe: menu, botones principales)
- --color-secundario: #3E2723 (cafe oscuro: pie de pagina)
- --color-acento: #E0A030     (ambar: detalles y alertas)
- --color-fondo: #FAF6F0      (fondo de la pagina)
- --color-texto: #2B2B2B      (texto)

## Logo
- static/img/logo.svg (una taza de cafe). Lo reemplaza cada equipo.

## Opciones del menu (izquierda)
Inicio | Menu | Carrito | Pedidos | Entregas | Reportes | Mis
direcciones | Administracion
- Cada una se muestra con el permiso indicado:
  Menu: catalogo.view_producto. Carrito: pedidos.add_pedido.
  Pedidos: pedidos.view_pedido (el texto es "Mis pedidos" si el
  usuario tiene pedidos.add_pedido). Entregas:
  pedidos.despachar_pedido. Reportes: pedidos.ver_reportes. Mis
  direcciones: cuentas.view_direccion.
- Esta aplicacion se usa sobre todo en el celular (RF-10, RNF-04):
  diseno movil primero; botones de accion grandes (btn btn-lg) en el
  menu del cliente y en las pantallas del barista y del repartidor.

## Pantalla del barista y del repartidor
- La lista de pedidos muestra tarjetas (no tabla) con el numero, la
  hora, los productos y un boton grande "Cambiar estado" (btn btn-lg
  w-100) que lleva a la accion de cambio de estado.

## Formato de numeros
- Los montos se muestran con simbolo y separador de miles:
  ${{ valor|floatformat:"0g" }}
