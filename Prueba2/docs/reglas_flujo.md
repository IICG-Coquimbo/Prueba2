# Reglas de flujo (logica de Cafe Rincon)

## Donde vive la logica
- En apps/pedidos/servicios.py y apps/pagos/servicios.py, como
  funciones normales (no son vistas). Las vistas las llaman desde
  form_valid y no repiten la logica.
- Cada funcion que toca varias tablas usa transaction.atomic().
- Si una regla no se cumple, la funcion lanza ValidationError con un
  mensaje en espanol; la vista lo muestra en el formulario.

## Estados del pedido
carrito -> recibido                      (pago en efectivo)
carrito -> pendiente_pago -> recibido    (pago con tarjeta aprobado)
pendiente_pago -> carrito                (pago con tarjeta fallido)
recibido -> en_preparacion -> listo_despacho -> en_camino -> entregado
- Las transiciones permitidas estan en un diccionario TRANSICIONES de
  apps/pedidos/servicios.py. Cualquier otra transicion es un error.
- Todo cambio de estado pasa por registrar_estado, que crea una fila
  de HistorialEstado (RNF-07).

## Funciones y requerimientos
- obtener_carrito(usuario): devuelve el pedido en estado carrito del
  usuario; si no existe, lo crea. (RF-04)
- agregar_item(pedido, producto, cantidad, opciones): exige estado
  carrito, producto disponible, cantidad mayor que 0, opciones que
  pertenezcan al producto y como maximo una por tipo (tamano, leche,
  azucar). precio_unitario = precio + recargos de las opciones. Llama
  a recalcular_totales. (RF-04, RF-05, RF-15)
- quitar_item(item): exige estado carrito. Llama a recalcular_totales.
- recalcular_totales(pedido): subtotal = suma de cantidad x
  precio_unitario; descuento = subtotal x porcentaje del codigo / 100
  (0 si no hay codigo); total = subtotal - descuento. Dos decimales.
- aplicar_codigo(pedido, texto): busca el CodigoDescuento por codigo.
  Exige activo, fecha de hoy entre vigente_desde y vigente_hasta y,
  si solo_primer_pedido, que el cliente no tenga otros pedidos fuera
  de carrito y pendiente_pago. Guarda el codigo en el pedido y llama a
  recalcular_totales. (RF-16)
- confirmar_pedido(pedido, direccion, metodo_pago): exige estado
  carrito, al menos un item y una direccion del mismo cliente. Crea el
  Pago (estado pendiente, referencia uuid4 en texto, monto = total).
  Efectivo: registrar_estado(recibido). Tarjeta:
  registrar_estado(pendiente_pago) y la vista redirige a la pasarela.
  (RF-07)
- resultado_pago(referencia, exitoso) en apps/pagos/servicios.py:
  exige Pago pendiente de metodo tarjeta. Exitoso: pago exitoso y
  pedido recibido. Fallido: pago fallido y pedido de vuelta a carrito.
  Un pago ya resuelto no se puede resolver otra vez. (RF-08, RNF-05)
- avanzar_pedido(pedido, nuevo_estado, usuario): valida con
  TRANSICIONES y por rol: preparar_pedido permite recibido ->
  en_preparacion y en_preparacion -> listo_despacho; despachar_pedido
  permite listo_despacho -> en_camino (crea la Entrega con ese
  repartidor e inicio = ahora) y en_camino -> entregado (solo el
  repartidor de la Entrega; guarda fin = ahora). (RF-12, RF-14)
- registrar_estado(pedido, nuevo_estado, usuario=None): cambia el
  estado y crea el HistorialEstado. (RNF-07)
- ventas_periodo(dias): suma del total de los pedidos en estado
  recibido o posterior creados en los ultimos <dias> dias (1 = hoy).
  (RF-17)
- productos_mas_pedidos(limite=5): productos con mas unidades en
  pedidos recibidos o posteriores. (RF-17)
- ranking_repartidores(): por repartidor, entregas con fin y minutos
  promedio, ordenado por entregas (mayor primero). (RF-18)

## Quien ve que pedido (filtro del queryset en las vistas)
- Cliente: sus pedidos; en "Mis pedidos" no aparece el carrito ni los
  pendientes de pago (el carrito se ve en /carrito/).
- Barista: estados recibido, en_preparacion y listo_despacho, del mas
  antiguo al mas nuevo. (RF-11)
- Repartidor: los listo_despacho, y los en_camino y entregado que son
  suyos. (RF-13)
- Administrador y Dueno: todos menos carrito.
- La direccion y el telefono del cliente se muestran solo a quien
  tiene despachar_pedido o es Administrador. (RF-13)

## Seguimiento
- El detalle del pedido muestra el estado y el historial con fecha y
  hora, y se recarga solo cada 15 segundos con
  <meta http-equiv="refresh" content="15"> dentro de un
  {% block extra_head %} de base.html. (RF-09, RNF-06, RNF-07)

## Pasarela de pago simulada
- Cafe Rincon no se conecta a una pasarela real. La app pagos incluye
  una pagina aparte, /pasarela/<referencia>/, que hace de pasarela
  externa: muestra el monto y dos opciones (RadioSelect: "Pago
  exitoso" y "Pago fallido"). Al enviar llama a resultado_pago y
  redirige al detalle del pedido con un mensaje. No pide ni guarda
  numeros de tarjeta. (RF-08, RNF-03, RNF-05)

## Decisiones del docente sobre requerimientos ambiguos
- RF-15 y RF-16: productos, categorias, opciones y codigos de
  descuento se administran en el admin de Django (usuario staff).
- RF-08 y RNF-05: la pasarela es simulada (ver arriba).
- RF-09 y RNF-06: "tiempo real" = recarga automatica cada 15 s.
- RF-03: las "fotos" son una URL (imagen_url), no archivos subidos.
- RF-16: "primer pedido" = el cliente no tiene pedidos recibidos o
  posteriores.
- RF-17: venta = total de un pedido en estado recibido o posterior.
- RF-18: tiempo promedio = minutos entre en_camino y entregado.
- RF-10 y RNF-04 piden lo mismo (responsive); se prueban juntos.
- RNF-01 (40 a 50 pedidos por hora) y RNF-02 (confirmar en pocos
  segundos) no se implementan ni se prueban con casos de usuario.
- RNF-03: las contrasenas usan el hash de Django; no existe ningun
  campo de tarjeta.

## Acciones y URLs
Las acciones son FormView con template accion_form.html. Formato:
URL, nombre, formulario, permiso, funcion.
- /menu/  producto_list (ListView: solo disponibles, salvo para quien
  tiene catalogo.change_producto)  catalogo.view_producto
- /menu/<id>/  producto_detail (DetailView con el formulario de abajo)
  catalogo.view_producto
- /menu/<id>/agregar/  producto_agregar
  AgregarAlCarritoForm (cantidad, y un Select opcional por cada tipo
  de opcion con las opciones de ese producto; el filtro va en
  __init__)  pedidos.add_pedido  agregar_item
- /carrito/  carrito_detail (items, totales, formulario de codigo y
  boton Confirmar; usa obtener_carrito)  pedidos.add_pedido
- /carrito/quitar/<id>/  item_quitar  QuitarItemForm (sin campos)
  pedidos.add_pedido  quitar_item
- /carrito/codigo/  carrito_codigo  CodigoForm (texto)
  pedidos.add_pedido  aplicar_codigo
- /carrito/confirmar/  carrito_confirmar  ConfirmarPedidoForm
  (direccion: Select solo con las direcciones del usuario;
  metodo_pago: RadioSelect)  pedidos.add_pedido  confirmar_pedido
- /pasarela/<referencia>/  pasarela  PasarelaForm (resultado:
  RadioSelect)  pedidos.add_pedido  resultado_pago
- /pedidos/  pedido_list (filtrada por rol)  pedidos.view_pedido
- /pedidos/<id>/  pedido_detail  pedidos.view_pedido
- /pedidos/<id>/estado/  pedido_estado  EstadoPedidoForm (estado:
  RadioSelect solo con el siguiente estado permitido para el rol; la
  orden llega en __init__)  pedidos.preparar_pedido o
  pedidos.despachar_pedido  avanzar_pedido
- /entregas/  entrega_list (listo_despacho y los del repartidor)
  pedidos.despachar_pedido
- /reportes/  reporte_panel (ventas de hoy y de 7 dias, productos mas
  pedidos)  pedidos.ver_reportes
- /reportes/repartidores/  reporte_repartidores (ranking)
  pedidos.ver_reportes
- /registro/  registro (CreateView, sin login)  cuentas:registro
- /direcciones/, /direcciones/nueva/, /direcciones/<id>/editar/,
  /direcciones/<id>/borrar/  direccion_list, _create, _update,
  _delete  cuentas.view/add/change/delete_direccion (solo propias)
