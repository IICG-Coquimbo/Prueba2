<<<<<<< HEAD

# Café Rincón: prueba de usuario paso a paso
En este ejercicio **no programas el sistema**: lo construyen agentes de OpenCode a partir de los requerimientos de `docs/requerimientos.csv`, y tú lo **pruebas como usuario**. Escribes escenarios de prueba, los ejecutas, y subes las capturas de pantalla como evidencia a un issue de GitHub.
Hay tres etapas. No pases a la siguiente si la actual tiene pruebas fallando.
| Etapa | Agentes | Qué pruebas | Dónde |
|---|---|---|---|
| 1 | `/agents` y `@modelos` | Entidades, relaciones y que la base de datos se genere | Admin de Django y `psql` |
| 2 | `@frontend`, `@formularios`, `@flujo`, `@vistas` | Que las vistas funcionen en el navegador | Navegador, como superusuario |
| 3 | `@usuarios` | Registro, login, roles y permisos | Navegador, un usuario por rol |
**Reglas del ejercicio**
1. El agente implementa el diseño que ya está en `docs/`; no inventa modelos, campos ni rutas.
2. Revisas el diff completo antes de aceptar cualquier cambio del agente.
3. **Los escenarios y casos de prueba los escribes tú**, no un agente ni otra herramienta de IA.
4. Todo comando de Django va por Docker: `docker compose exec web python manage.py ...`. Nunca ejecutes `python`, `pip` ni `manage.py` directo en tu computador.
5. Nunca ejecutes `docker compose down -v` sin permiso: borra la base de datos.
---
## 0. Antes de empezar
Necesitas: Docker Desktop, Git, VS Code, OpenCode y una cuenta de GitHub con acceso al repositorio del curso.
**Clonar y preparar el entorno**
```
git clone https://github.com/OWNER/REPO.git
cd REPO
```
Copia el archivo de variables:
- Windows (cmd): `copy .env.example .env`
- macOS: `cp .env.example .env`
Levanta los servicios y comprueba que estén corriendo:
```
docker compose up --build -d
docker compose ps
```
Deben aparecer `web` y `db`. Si `web` no está corriendo, mira el motivo con `docker compose logs --tail 40 web`.
**Trabajarás en una rama por etapa**, nunca directo en `main`:
```
git switch -c etapa-1-modelos
```
---
## 1. Cómo documentas una prueba
### 1.1 El escenario (issue en GitHub)
Un **escenario** agrupa casos de una misma función. Cada **caso** es una prueba concreta. Es una fila de la planilla Quiz, y vive en un issue.
1. En el repositorio: **Issues → New issue → Escenario de prueba**.
2. Completa el formulario:
   | Campo | Qué escribes |
   |---|---|
   | Sprint | El sprint en curso |
   | ID del escenario | `TS_01`, `TS_02`... (y el título del issue empieza con `[TS_01]`) |
   | Requerimientos | Los ids **exactos** del CSV, por ejemplo `RF-03, RF-05, RF-15` (con guion) |
   | Descripción | Qué función se prueba |
   | Importancia | Alta, Media o Baja |
   | Etapa | La etapa en que se prueba |
   | Casos de prueba | Una tarea por caso: `- [ ] CP-01: ...` |
   | Precondiciones, pasos y resultado esperado | Con qué usuario, qué datos deben existir, una acción por línea y qué debes ver |
3. El issue nace con la etiqueta `estado:SP` (sin pruebas).
**Cada caso debe decir, como mínimo:** qué usuario lo ejecuta, qué datos deben existir antes, los pasos (una acción por línea) y el resultado esperado. Incluye casos **positivos** (todo bien) y **negativos** (campo vacío, valor repetido, permiso que falta).
### 1.2 La ejecución y la evidencia
Cada vez que ejecutas el escenario, escribes **un comentario nuevo** en el issue con esta plantilla (`docs/plantilla_evidencia.md`):
```
**Ejecucion:** No. 1
**Fecha:** AAAA-MM-DD
**Ejecutado por:** @tu-usuario-github (usuario del sistema: admin1)
**Casos ejecutados:** CP-01, CP-02
**Estado:** P / R / B / SE / NR / SP
**Resultado real:** (qué viste, en una o dos frases)
**Evidencia**
1. CP-01, paso 3: (captura)
2. CP-01, resultado final: (captura)
**Defecto asociado:** #__ (si hubo)
```
Para subir una captura, **arrástrala al cuadro de comentario**: GitHub la sube sola.
**Una captura válida:**
- Muestra la **barra de direcciones** (la URL) y el **usuario conectado**.
- Muestra el **resultado**, no solo el formulario vacío. Si hay un error, la pantalla completa del error.
- En comandos, la ventana de la terminal con el comando y su salida.
- Nombre sugerido: `E<etapa>-<número>.png`, por ejemplo `E1-05.png`.
- Atajos: Windows `Windows + Mayús + S`; macOS `Cmd + Mayús + 4`.
### 1.3 El estado del escenario
Quita la etiqueta `estado:` anterior y pon la nueva (panel **Labels** del issue):
| Etiqueta | Significado | Cuándo |
|---|---|---|
| `estado:SP` | Sin pruebas | Escrito, no ejecutado |
| `estado:NR` | No realizada | Se intentó y no se pudo ejecutar |
| `estado:P` | Errores | Algún caso falló |
| `estado:R` | Regular | Pasan algunos casos y otros no, o pasan con observaciones |
| `estado:SE` | Errores solucionados | Falló, el agente lo corrigió y ahora pasa |
| `estado:B` | Bien | Todos pasaron a la primera |
El porcentaje de avance lo calcula GitHub con las tareas marcadas (`- [x]`) de la lista de casos.
### 1.4 Si algo falla
1. Crea un issue **Defecto encontrado**: escenario donde apareció, resultado esperado, resultado obtenido (mensaje de error y captura) y clasificación:
   - **Defecto del sistema:** el requerimiento está claro y el sistema no lo cumple.
   - **Caso mal escrito:** el sistema hace lo correcto; tu caso esperaba otra cosa o le faltaba una precondición.
   - **Requerimiento ambiguo:** hay dos lecturas razonables; hay que acordar cuál es la correcta.
2. Si es del sistema, pide la corrección al agente, con lo esperado, lo obtenido y el error, y limitando el alcance:
   > Al abrir /carrito/ sale NoReverseMatch para 'carrito_codigo'. Esperado: la página del carrito (docs/reglas_flujo.md, sección Acciones y URLs). Corrige solo lo necesario en apps/pedidos, muestra el diff y ejecuta la revisión de templates.
3. Ejecuta de nuevo el escenario. Si pasa, etiqueta `estado:SE`.
Si el mismo error vuelve después de dos intentos, avisa al docente: puede que la regla esté ambigua.
---
## 2. Etapa 1: modelos y base de datos (`@modelos`)
**Objetivo:** comprobar que las entidades y relaciones existen y que la base de datos se genera. Todavía no hay pantallas del sistema: se prueba en el admin de Django.
### Pasos
1. **Rama y entorno.** `git switch -c etapa-1-modelos`. Comprueba `docker compose ps`. *Evidencia E1-01.*
2. **Elegir el agente.** En la terminal de VS Code ejecuta `opencode`, escribe `/agents` y elige `modelos`. Si no aparece, revisa que exista la carpeta `.opencode/agents/` (algunas versiones usan `.opencode/agent/`).
3. **Pedir:**
   > @modelos implementa los modelos y el admin de cuentas, catalogo, promociones, pedidos, pagos y entregas según docs/modelo_datos.md.
4. **Revisar el diff antes de aceptar.** Comprueba que:
   - cada `ForeignKey` tenga `related_name` y `on_delete`;
   - el dinero sea `DecimalField`;
   - los estados usen `TextChoices`;
   - `Pedido` tenga los tres permisos propios (`preparar_pedido`, `despachar_pedido`, `ver_reportes`);
   - cada modelo tenga `__str__` y esté en `admin.py`.
   Si falta algo, pídeselo al agente. Haz un commit: `git add .` y `git commit -m "@modelos: modelos y admin"`.
5. **Migraciones:**
   ```
   docker compose exec web python manage.py makemigrations
   docker compose exec web python manage.py migrate
   ```
   Deben crear migraciones en las seis apps y terminar sin errores. *Evidencias E1-02 y E1-03.*
6. **La base de datos se generó.** Las credenciales salen de tu `.env` (aquí `userBD` y `BDPrueba`):
   ```
   docker compose exec db psql -U userBD -d BDPrueba -c "\dt"
   docker compose exec db psql -U userBD -d BDPrueba -c "\d pedidos_pedido"
   ```
   El primero lista las tablas: deben estar las 11 de los modelos y la tabla intermedia `pedidos_itempedido_opciones`. El segundo muestra las columnas y claves foráneas de `pedidos_pedido`. *Evidencias E1-04 y E1-05.*
7. **Superusuario:**
   ```
   docker compose exec web python manage.py createsuperuser
   ```
   Entra a <http://localhost:8000/admin/>. *Evidencia E1-06:* el índice del admin con las seis secciones.
8. **Probar entidades y relaciones en el admin.** Crea los datos **en este orden** (cada uno necesita el anterior): categoría, producto, opciones, código de descuento, usuario, perfil, dirección, pedido, ítems (con opciones), historial, pago y entrega. Qué verificar en cada modelo:
   | Modelo | Qué probar |
   |---|---|
   | PerfilCliente | Un usuario solo puede tener un perfil (uno a uno) |
   | Direccion | Un usuario con varias direcciones |
   | Categoria | Nombre repetido: error. Borrar una categoría con productos: no se deja |
   | Producto | Categoría elegida de una lista; `disponible` marcado por defecto |
   | OpcionProducto | Tipo con 3 opciones (tamaño, leche, azúcar); recargo 0 por defecto |
   | CodigoDescuento | Código repetido: error |
   | Pedido | Estado con 7 opciones y `carrito` por defecto; fecha automática |
   | ItemPedido | Varias opciones a la vez (selector múltiple). Borrar el pedido borra sus ítems |
   | HistorialEstado | Fecha automática (RNF-07) |
   | Pago | No existe ningún campo de tarjeta (RNF-03). Un pedido, un pago |
   | Entrega | Un pedido, una entrega |
   Otras comprobaciones, cada una con captura:
   - **Textos legibles:** las listas muestran nombres, no "Direccion object (1)".
   - **Contraseña con hash (RNF-03):** en el detalle de un usuario, la contraseña empieza con `pbkdf2_sha256$`.
   - **Permisos propios:** ejecuta `docker compose exec web python manage.py shell` y escribe:
     ```python
     from django.contrib.auth.models import Permission
     list(Permission.objects.filter(content_type__app_label="pedidos", codename__in=["preparar_pedido", "despachar_pedido", "ver_reportes"]).values_list("codename", flat=True))
     ```
     Deben aparecer los tres. Sal con `exit()`.
9. **Escribe los escenarios** (mínimo 6, uno por app con modelos), ejecútalos y sube la evidencia (sección 1).
10. **Antes de cerrar:** borra los datos de prueba del admin, o usa nombres de usuario distintos de `admin1`, `cliente1`, etc., para que no choquen con los datos de demostración de la etapa 3.
11. **Cerrar la etapa:**
    ```
    git push -u origin etapa-1-modelos
    ```
    Abre el pull request. La plantilla pide marcar el agente, confirmar que revisaste el diff y enlazar los issues (`Refs #12`). No se fusiona hasta tener la evidencia de la etapa completa.
**Cobertura mínima:** la estructura de todos los modelos, RNF-03 (hash y ningún campo de tarjeta) y RNF-07 (existe el historial de estados).
---
## 3. Etapa 2: las vistas (`@frontend`, `@formularios`, `@flujo`, `@vistas`)
**Objetivo:** que cada vista funcione de punta a punta en el navegador. Todavía no existe el login (lo crea `@usuarios` en la etapa 3), así que pruebas **como superusuario**: entras por `/admin/` y, con esa sesión, abres el resto del sistema. El superusuario tiene todos los permisos, así que una misma persona hace de cliente, barista, repartidor y dueño. Quién puede hacer qué se prueba en la etapa 3.
### Pasos
1. **Rama** desde `main` actualizada: `git switch -c etapa-2-vistas`.
2. **Los agentes, de a uno y en este orden.** Después de cada uno: revisa el diff, ejecuta la revisión de templates y `check` (paso 3) y haz un commit.
   1. > @frontend crea base.html, el menú, el pie, 403.html, estilos.css y el home, y configura static, templates y mensajes.
   2. > @formularios crea los formularios de todas las apps, incluidos los de acción.
   3. > @flujo crea servicios.py de pedidos y pagos según docs/reglas_flujo.md.
   4. > @vistas crea las vistas, urls y templates de catalogo.
      Se repite para `pedidos`, `pagos`, `entregas` y `reportes`, una app por vez. (`cuentas` y el login quedan para `@usuarios`.)
   También puedes pedir todo al maestro: `@maestro actualiza todo`. Se detiene al final de cada agente para que hagas los puntos de esa etapa.
3. **Revisión de templates y `check`** (mismo comando en Windows y macOS):
   ```
   docker compose exec web python manage.py shell -c "exec(open('revisar_templates.py').read())"
   docker compose exec web python manage.py check
   ```
   Debe imprimir `templates OK` y `System check identified no issues`. No detecta nombres de URL que no existen: esos se ven al abrir la página.
4. **Estilos.** Abre <http://localhost:8000/static/css/estilos.css>: debe verse el CSS. Si no: `docker compose exec web python manage.py findstatic css/estilos.css`.
5. **Entrar.** Entra a `/admin/` con tu superusuario y luego abre <http://localhost:8000/>. Verás el home con el menú completo. Para salir usa *Cerrar sesión* del admin. Hasta la etapa 3, `/login/` no existe: es normal.
6. **Datos para probar** (en el admin): una categoría; un producto disponible con foto (cualquier URL de imagen) y opciones de tamaño, leche y azúcar; un producto **no disponible**; el código `BIENVENIDA10` (10 %, vigente hoy); y una **dirección** para tu usuario (el superusuario es el cliente en esta etapa).
7. **Escribe los escenarios** de la cobertura de esta etapa, ejecútalos con el mapa de abajo y sube las evidencias.
### Mapa de lo que ya se puede probar
Es un mapa de qué mirar, no los escenarios: esos los escribe cada equipo.
| Página | Qué debe funcionar | Req. |
|---|---|---|
| `/menu/` | Solo productos disponibles, con foto y precio. El no disponible no aparece (cámbialo en el admin y recarga) | RF-03, RF-15 |
| `/menu/<id>/` | Producto con opciones; elegir tamaño, leche, azúcar y cantidad, y agregar al carrito. Con cantidad 0, error en el formulario | RF-04, RF-05 |
| `/carrito/` | Ítems, subtotal y total: comprueba a mano que sea cantidad × (precio + recargos). Quitar un ítem actualiza los totales | RF-04 |
| `/carrito/codigo/` | Un código válido descuenta el 10 %. Vencido (pon la vigencia en el pasado), inexistente o inactivo: error | RF-16 |
| `/carrito/confirmar/` | Elegir dirección y pago. Efectivo: el pedido queda `recibido`. Sin ítems o sin dirección: error | RF-07 |
| `/pasarela/<ref>/` | Pago con tarjeta: *Pago exitoso* deja el pedido `recibido` y el pago `exitoso`; *Pago fallido* devuelve el pedido a `carrito` con un mensaje. Comprueba en el admin que no hay datos de tarjeta | RF-08, RNF-05, RNF-03 |
| `/pedidos/<id>/` | Estado e historial con fecha y hora. Abre el detalle en una pestaña, cambia el estado en otra y espera 15 segundos: se actualiza sola | RF-09, RNF-06, RNF-07 |
| `/pedidos/` | Cola de pedidos del más antiguo al más nuevo, con productos y variantes | RF-11 |
| `/pedidos/<id>/estado/` | Solo ofrece el siguiente estado permitido: recibido, en preparación, listo para despacho | RF-12 |
| `/entregas/` | Pedidos listos con dirección y contacto del cliente. Pasarlos a en camino y entregado; en el admin aparece la entrega con inicio y fin | RF-13, RF-14 |
| `/reportes/` | Ventas de hoy y de 7 días y productos más pedidos; deben coincidir con los pedidos que hiciste | RF-17 |
| `/reportes/repartidores/` | Ranking de repartidores con entregas y minutos promedio | RF-18 |
| Móvil | Con F12 y modo dispositivo (Ctrl+Mayús+M), 375 px de ancho: el menú se colapsa, las listas son tarjetas y los botones son grandes | RF-10, RNF-04 |
Las rutas son cortas y con el nombre del recurso (`/menu/`, `/carrito/`). Si ves `/nuevo/` a secas, es un defecto.
**Cobertura mínima:** RF-03, RF-04, RF-05, RF-07, RF-08, RF-09, RF-11, RF-12, RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-10 y RNF-04, RNF-05, RNF-06, RNF-07.
**Cerrar la etapa:** `git push -u origin etapa-2-vistas` y pull request, igual que en la etapa 1.
---
## 4. Etapa 3: usuarios y roles (`@usuarios`)
**Objetivo:** probar el registro, el inicio de sesión y que cada rol ve y hace solo lo que le corresponde.
### Pasos
1. **Rama:** `git switch -c etapa-3-usuarios` desde `main` con la etapa 2 fusionada.
2. **Pedir:**
   > @usuarios crea el login, logout, registro, las direcciones del cliente y el comando crear_roles según docs/roles.md.
   Revisa el diff, ejecuta la revisión de templates y `check`, y haz commit.
3. **Roles y usuarios de demostración:**
   ```
   docker compose exec web python manage.py crear_roles --demo
   ```
   Ejecútalo **dos veces**: la segunda no debe duplicar nada. *Evidencia E3-01.* Si borraste el volumen, se repite.
4. **Escribe los escenarios** (uno por rol, más registro, login y accesos denegados) y ejecútalos con los usuarios de la tabla. Para probar dos roles a la vez, usa una ventana privada.
| Usuario | Rol | Menú que debe ver |
|---|---|---|
| `cliente1` | Cliente | Inicio, Menú, Carrito, Mis pedidos, Mis direcciones |
| `barista1` | Barista | Inicio, Pedidos |
| `repartidor1`, `repartidor2` | Repartidor | Inicio, Entregas |
| `dueno1` | Dueño | Inicio, Reportes |
| `admin1` | Administrador | Inicio, Pedidos, Administración (es staff) |
Clave de todos: `clave1234` (solo para el curso).
### Qué se puede probar
- **Registro (RF-01):** `/registro/` crea una cuenta de cliente y entra al inicio. Campos vacíos o correo repetido muestran errores. En el admin, la contraseña tiene hash (RNF-03) y el usuario está en el grupo Cliente.
- **Login y logout (RF-02):** datos correctos entran al home; incorrectos muestran un error; *Salir* termina la sesión, y abrir cualquier página sin sesión lleva al login.
- **Direcciones (RF-06):** `cliente1` crea *Trabajo*, la edita y la borra. Un segundo cliente (el que se registró) no ve las de `cliente1`.
- **Menú por rol:** una captura del menú de cada uno de los cinco roles; deben coincidir con la tabla.
- **Accesos denegados:** con la sesión abierta, escribe la URL a mano; debe aparecer la página 403 ("No tienes permiso para ver esta página").
| Usuario | URL | Esperado |
|---|---|---|
| `cliente1` | `/reportes/` | 403 |
| `cliente1` | `/entregas/` | 403 |
| `barista1` | `/entregas/` | 403 |
| `barista1` | `/carrito/` | 403 |
| `repartidor1` | `/menu/` | 403 |
| `dueno1` | `/carrito/` | 403 |
| `dueno1` | `/pedidos/<id>/estado/` | 403 |
| Sin sesión | `/pedidos/` | Lleva a `/login/` |
- **Recorrido con roles reales:** repite el recorrido de la etapa 2 con la persona correcta en cada paso. `cliente1` arma el pedido y paga; `barista1` lo prepara; `repartidor1` lo entrega; `dueno1` ve los reportes. Cada uno debe poder hacer su parte y solo su parte.
- **Visibilidad de pedidos:** `cliente1` no ve los pedidos de otro cliente; `repartidor2` no puede marcar como entregado un pedido que lleva `repartidor1`; el barista no ve pedidos en carrito.
- **Administrador (RF-15, RF-16):** `admin1` entra al admin, marca un producto como no disponible y crea un código de descuento; `cliente1` comprueba que el producto no aparece y que el código funciona.
**Cobertura mínima:** RF-01, RF-02, RF-06 y los permisos de cada rol sobre lo probado en la etapa 2, incluidos los accesos denegados.
**Cerrar la etapa:** `git push -u origin etapa-3-usuarios` y pull request.
---
## 5. Qué entregas
- [ ] Los tres pull requests de etapa fusionados en `main`.
- [ ] Todos tus escenarios con estado distinto de `SP` y su evidencia en comentarios.
- [ ] Los defectos en issues, clasificados y cerrados o explicados.
- [ ] Cada requerimiento de `docs/requerimientos.csv` aparece en al menos un escenario (excepto RNF-01 y RNF-02, que no se prueban con casos de usuario).
---
## 6. Problemas frecuentes
| Síntoma | Qué hacer |
|---|---|
| `service "web" is not running` | Falta `docker compose up -d` |
| `password authentication failed` | Cambiaste el `.env` después de crear el volumen: `docker compose down -v` (borra la base, pide permiso) y vuelve a levantar |
| `makemigrations` no detecta una app | Falta en `INSTALLED_APPS`, o su `name` en `apps.py` no es `apps.<nombre>` |
| El CSS no carga | `static/` debe estar junto a `manage.py`; usa `findstatic` |
| `TemplateSyntaxError` | Etiqueta mal cerrada (`%>`) o un `if` de una línea al estilo Python; la revisión de templates dice qué archivo |
| `NoReverseMatch` | Un template usa un nombre de URL que no existe; revisa `docs/reglas_flujo.md` y pide la corrección a `@vistas` |
| Los formularios salen sin campos | El partial `form_campos.html` debe ser el de `docs/reglas_formularios.md` |
| Redirige a `/accounts/login/` (404) | Estás en la etapa 2: entra por `/admin/` (el login llega en la etapa 3) |
| `/login/` da `TemplateDoesNotExist` | Falta ejecutar `@frontend` (etapa 2) |
| El formulario de issue no pone etiquetas | Las etiquetas no existían: el docente ejecuta `python herramientas/etiquetas.py OWNER/REPO` y creas el issue de nuevo |
| La imagen del issue no se ve | Arrastra la imagen al cuadro de comentario; si es un enlace, el repositorio privado solo lo muestra a quien tiene acceso |
| La tarea no suma al avance | La línea debe empezar con `- [ ]` (guion, espacio, corchetes) |
Displaying README.md.Inserted margareth.cleveland@ucn.cl.
=======
# Franco Paredes Vivar
RUT: 21.714.507-4
>>>>>>> f9fdd0233bc98331bd0fb12c3cfe37afc0ab0aa2
