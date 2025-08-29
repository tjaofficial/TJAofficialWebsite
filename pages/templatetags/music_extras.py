from django import template
register = template.Library()

@register.filter
def mmss(seconds):
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        seconds = 0
    m, s = divmod(max(0, seconds), 60)
    return f"{m}:{s:02d}"
