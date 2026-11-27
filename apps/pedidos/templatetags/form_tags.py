from django import template

register = template.Library()


@register.filter
def widget_type(field):
    """Retorna el nombre de la clase del widget (ej: 'RadioSelect', 'Select', 'TextInput')"""
    return field.field.widget.__class__.__name__