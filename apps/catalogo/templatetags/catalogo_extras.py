from django import template

register = template.Library()


@register.filter
def split(value, arg):
    """Divide una cadena por el separador dado y devuelve una lista."""
    try:
        return value.split(arg)
    except (AttributeError, TypeError):
        return []
