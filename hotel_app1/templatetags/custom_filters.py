# custom_filters.py

from django import template

register = template.Library()

@register.filter
def get_value_from_key(dictionary, key):
    return dictionary.get(int(key))
