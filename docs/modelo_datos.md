# Modelo de datos - Cafe Rincon

Diseno de referencia del docente. Si el equipo disena su propio
modelo, reemplaza este archivo antes de usar el agente @modelos.

## App cuentas

### PerfilCliente
- usuario: OneToOneField(User, related_name="perfil",
  on_delete=CASCADE)
- telefono: CharField(20)

### Direccion
- usuario: ForeignKey(User, related_name="direcciones",
  on_delete=CASCADE)
- alias: CharField(40) (ejemplo: Casa, Trabajo)
- direccion: CharField(200)
- referencia: CharField(200), opcional

## App catalogo

### Categoria
- nombre: CharField(80), unico

### Producto
- categoria: ForeignKey(Categoria, related_name="productos",
  on_delete=PROTECT)
- nombre: CharField(120)
- descripcion: TextField, opcional
- precio: DecimalField(10, 2)
- imagen_url: URLField, opcional (direccion de una foto en internet)
- disponible: BooleanField, por defecto True

### OpcionProducto
- producto: ForeignKey(Producto, related_name="opciones",
  on_delete=CASCADE)
- tipo: CharField(10) con opciones: tamano, leche, azucar
- nombre: CharField(60) (ejemplo: Grande, Avena, Sin azucar)
- recargo: DecimalField(10, 2), por defecto 0

## App promociones

### CodigoDescuento
- codigo: CharField(20), unico (ejemplo: BIENVENIDA10)
- porcentaje: PositiveIntegerField (entre 1 y 100)
- vigente_desde: DateField
- vigente_hasta: DateField
- solo_primer_pedido: BooleanField, por defecto False
- activo: BooleanField, por defecto True

## App pedidos

### Pedido
- cliente: ForeignKey(User, related_name="pedidos",
  on_delete=PROTECT)
- estado: CharField(20) con opciones: carrito, pendiente_pago,
  recibido, en_preparacion, listo_despacho, en_camino, entregado.
  Por defecto: carrito. (Un pedido es primero el carrito del cliente.)
- direccion: ForeignKey(cuentas.Direccion, related_name="pedidos",
  null, blank, on_delete=SET_NULL)
- metodo_pago: CharField(10) con opciones: efectivo, tarjeta.
  Opcional (vacio mientras es carrito).
- codigo_descuento: ForeignKey(promociones.CodigoDescuento,
  related_name="pedidos", null, blank, on_delete=SET_NULL)
- subtotal: DecimalField(10, 2), por defecto 0
- descuento: DecimalField(10, 2), por defecto 0
- total: DecimalField(10, 2), por defecto 0
- creado: DateTimeField, automatica al crear
- Permisos propios (Meta.permissions): preparar_pedido,
  despachar_pedido, ver_reportes

### ItemPedido
- pedido: ForeignKey(Pedido, related_name="items", on_delete=CASCADE)
- producto: ForeignKey(catalogo.Producto, related_name="items",
  on_delete=PROTECT)
- cantidad: PositiveIntegerField, por defecto 1
- precio_unitario: DecimalField(10, 2) (precio del producto mas los
  recargos de las opciones, calculado al agregar)
- opciones: ManyToManyField(catalogo.OpcionProducto,
  related_name="items", blank)

### HistorialEstado
- pedido: ForeignKey(Pedido, related_name="historial",
  on_delete=CASCADE)
- estado: CharField(20), con las mismas opciones de Pedido.estado
- fecha: DateTimeField, automatica al crear
- usuario: ForeignKey(User, related_name="cambios_estado", null,
  on_delete=SET_NULL)

## App pagos

### Pago
- pedido: OneToOneField(pedidos.Pedido, related_name="pago",
  on_delete=CASCADE)
- metodo: CharField(10) con opciones: efectivo, tarjeta
- estado: CharField(10) con opciones: pendiente, exitoso, fallido.
  Por defecto: pendiente.
- referencia: CharField(36), unico (texto de un uuid)
- monto: DecimalField(10, 2)
- fecha: DateTimeField, automatica al crear
- No tiene ningun campo para numero de tarjeta (RNF-03).

## App entregas

### Entrega
- pedido: OneToOneField(pedidos.Pedido, related_name="entrega",
  on_delete=CASCADE)
- repartidor: ForeignKey(User, related_name="entregas",
  on_delete=PROTECT)
- inicio: DateTimeField (cuando pasa a en_camino)
- fin: DateTimeField, null, blank (cuando pasa a entregado)
- Propiedad minutos (no es un campo): minutos entre inicio y fin, o
  None si aun no termina.

## App reportes
Sin modelos. Solo vistas (ver docs/reglas_flujo.md).
