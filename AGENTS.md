# Proyecto Django con Docker

## Entorno
- Stack: Django 5 + PostgreSQL, todo dentro de Docker
  (docker-compose.yml). Servicios: web y db.
- TODO comando de Django se ejecuta dentro del contenedor:
  docker compose exec web python manage.py <comando>
  Si web no esta corriendo:
  docker compose run --rm web python manage.py <comando>
- Nunca ejecutes python, pip ni manage.py directo en el computador.
- Si cambia requirements.txt hay que reconstruir:
  docker compose up --build -d
- Nunca ejecutes docker compose down -v sin permiso expreso del
  estudiante: borra la base de datos.
- Antes de ejecutar un comando de Docker, di cual es y para que.

## Paquete del proyecto
- En estas reglas <proyecto> es el nombre de la carpeta de
  configuracion de Django: la que contiene settings/ y urls.py (por
  ejemplo taller_proyecto). Se ve en DJANGO_SETTINGS_MODULE de
  docker-compose.yml (<proyecto>.settings.local). Usa siempre el
  nombre real, nunca escribas "<proyecto>" literal.
- <settings> es el archivo de settings: <proyecto>/settings.py, o
  <proyecto>/settings/base.py si el proyecto lo dividio por entornos.
  Edita el que exista; NUNCA crees el otro ni cambies BASE_DIR.

## Estructura
- Las apps van en apps/<nombre>.
- Las apps salen de docs/modelo_datos.md: cada "## App <nombre>" es
  una carpeta apps/<nombre>. Ademas existen siempre apps/inicio y
  apps/cuentas (y apps/pruebas solo si el modelo la define).

## Fuentes de verdad
- Del caso: docs/modelo_datos.md, docs/requerimientos.csv,
  docs/identidad.md, docs/roles.md y docs/reglas_flujo.md.
- Generales: docs/reglas_base_datos.md, reglas_formularios.md,
  reglas_vistas_templates.md, reglas_frontend.md, reglas_usuarios.md
  (y reglas_pruebas_usuario.md si el caso usa pruebas).
- El codigo se ajusta a los docs, nunca al reves. No cambies un doc
  si no te lo piden. No inventes modelos, campos ni requerimientos.

## Revision de templates (obligatoria)
Despues de escribir o cambiar templates ejecuta este comando; compila
todos y falla con el nombre del archivo si alguno tiene un error de
sintaxis:
  docker compose exec web python manage.py shell -c "import glob; from django.template.loader import get_template; [get_template(p.split('templates/', 1)[1]) for p in glob.glob('**/templates/**/*.html', recursive=True)]; print('templates OK')"
Si no imprime "templates OK", corrige antes de seguir. No detecta
nombres de URL que no existen: esos se ven al abrir la pagina.

## Forma de trabajar
- Despues de cualquier cambio, muestra el diff y espera confirmacion.
- Si ya existe algo que coincide con los docs, no lo toques.
- Hay un agente por tema (@modelos, @frontend, @formularios, @flujo,
  @vistas, @usuarios y, si el caso lo usa, @pruebas) y un agente
  @maestro que los
  coordina. Cada uno toca solo sus archivos.
- Nunca escribas casos de prueba de usuario: los escriben los
  estudiantes.
