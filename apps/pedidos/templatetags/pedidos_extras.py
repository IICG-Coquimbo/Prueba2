from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def mul(value, arg):
    """Multiplica dos valores."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return ''


@register.filter
def div(value, arg):
    """Divide dos valores."""
    try:
        return Decimal(str(value)) / Decimal(str(arg))
    except (ValueError, TypeError, ZeroDivisionError):
        return ''