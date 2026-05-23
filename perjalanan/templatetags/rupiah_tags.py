from django import template

register = template.Library()

@register.filter(name='rupiah')
def rupiah(value):
    try:
        if value is None or value == '':
            return "0"
        val = float(value)
        return f"{val:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return value
