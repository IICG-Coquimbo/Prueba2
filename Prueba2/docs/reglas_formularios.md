# Reglas de formularios

- Todo formulario de un modelo es un ModelForm en apps/<app>/forms.py,
  con nombre <Modelo>Form (ejemplo: ClienteForm).
- En Meta usa model y una lista explicita fields. NUNCA
  fields = "__all__" ni exclude.
- Solo incluye campos que existan en docs/modelo_datos.md.
- labels en espanol para todos los campos.
- widgets (Bootstrap 5):
  - texto: forms.TextInput(attrs={"class": "form-control"})
  - numeros: forms.NumberInput(attrs={"class": "form-control"})
  - correo: forms.EmailInput(attrs={"class": "form-control"})
  - ForeignKey y opciones: forms.Select(attrs={"class": "form-select"})
  - booleanos: forms.CheckboxInput(attrs={"class": "form-check-input"})
  - fechas: forms.DateInput(format="%Y-%m-%d",
    attrs={"class": "form-control", "type": "date"})
  - textos largos: forms.Textarea(attrs={"class": "form-control",
    "rows": 3})
  - opciones con radio: forms.RadioSelect
  - varias opciones: forms.CheckboxSelectMultiple
- Validaciones: un campo con clean_<campo>(); varios campos con
  clean() y self.add_error("<campo>", "mensaje"). Mensajes en espanol.
- Formularios de ACCION (no editan un modelo completo): son
  forms.Form con pocos campos, o ModelForm con un solo campo. Los
  necesarios estan en la seccion "Acciones y URLs" de
  docs/reglas_flujo.md. Cuando un campo de seleccion debe mostrar solo
  algunas opciones (por ejemplo solo los disponibles), el filtro se
  hace en __init__ del formulario.
- Formularios de usuario (apps/cuentas/forms.py): LoginForm hereda de
  AuthenticationForm; en __init__ agrega la clase form-control a cada
  campo.
- Dibujo: un solo partial, templates/parciales/form_campos.html.
  Ninguna pagina dibuja campos a mano. Se incluye SIN parametros con
  {% include "parciales/form_campos.html" %}, dentro del <form>: el
  partial recorre el formulario (variable form) por su cuenta. Su
  contenido es EXACTAMENTE este (copialo tal cual):

  {% if form.non_field_errors %}
  <div class="alert alert-danger">{{ form.non_field_errors }}</div>
  {% endif %}
  {% for oculto in form.hidden_fields %}{{ oculto }}{% endfor %}
  {% for campo in form.visible_fields %}
  <div class="mb-3">
    {% if campo.field.widget.input_type == "checkbox" %}
    <div class="form-check">
      {{ campo }}
      <label class="form-check-label" for="{{ campo.id_for_label }}">{{ campo.label }}</label>
    </div>
    {% else %}
    <label class="form-label" for="{{ campo.id_for_label }}">{{ campo.label }}{% if campo.field.required %} *{% endif %}</label>
    {{ campo }}
    {% endif %}
    {% if campo.help_text %}<div class="form-text">{{ campo.help_text }}</div>{% endif %}
    {% for error in campo.errors %}<div class="text-danger small">{{ error }}</div>{% endfor %}
  </div>
  {% endfor %}

  Cada etiqueta {% %} se cierra con %}; nunca con %>.
- No toques views.py, models.py ni urls.py.
