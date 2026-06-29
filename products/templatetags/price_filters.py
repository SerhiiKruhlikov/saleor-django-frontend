# products/templatetags/price_filters.py
from django import template
from django.template.defaultfilters import floatformat
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.filter
def price_format(value):
    """
    Применяет формат: округление до целого, добавление разделителей тысяч и замена запятой на пробел.
    Например: 132525 → 132 525
    """
    try:
        rounded = floatformat(value, 0)
        comma_formatted = intcomma(rounded)
        return comma_formatted.replace(",", " ")
    except Exception:
        return value
