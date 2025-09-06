# pages/templatetags/shop_extras.py
from django import template

register = template.Library()

@register.filter
def money(cents):
    try:
        return f"${(int(cents)/100):.2f}"
    except Exception:
        return "$0.00"
