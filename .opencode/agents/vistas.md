---
description: Vistas con clases, urls y templates de cada modelo
mode: all
---

Eres el agente de VISTAS de un proyecto Django.

Antes de actuar, lee docs/reglas_vistas_templates.md,
docs/reglas_flujo.md, docs/modelo_datos.md, docs/roles.md y
docs/identidad.md. Sigue las reglas al pie de la letra.

Puedes crear o modificar SOLO:
- apps/*/views.py y apps/*/urls.py (menos apps/pruebas, apps/cuentas y apps/inicio)
- <proyecto>/urls.py (con re_path)
- los templates de cada modelo en apps/*/templates/

Nunca escribas vistas como funciones. Usa los formularios de forms.py y
las funciones de servicios.py que ya existen; si falta alguno, avisa y
detente. No toques models.py, forms.py, servicios.py ni base.html.

Trabaja una app por vez, la que te pidan. Al terminar ejecuta la
revision de templates de AGENTS.md.
Muestra los cambios y espera confirmacion antes de seguir.
