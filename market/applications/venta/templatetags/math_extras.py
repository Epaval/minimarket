# venta/templatetags/math_extras.py
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """
    Multiplica dos números: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0