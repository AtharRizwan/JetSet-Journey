"""Wrappers around the third-party HTTP APIs used by the views.

Every function returns None when the API key is missing or the request fails,
so pages keep rendering without network access.
"""
import os

import requests
from django.core.cache import cache

TIMEOUT = 5
WEATHER_CACHE_SECONDS = 10 * 60


def _get_json(url, **kwargs):
    try:
        response = requests.get(url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def get_weather_data(city):
    api_key = os.environ.get('WEATHERAPI_KEY')
    if not api_key or not city:
        return None
    cache_key = f'weather:{city.lower()}'
    data = cache.get(cache_key)
    if data is None:
        data = _get_json(
            'https://api.weatherapi.com/v1/current.json',
            params={'key': api_key, 'q': city, 'aqi': 'no'},
        )
        if data is not None:
            cache.set(cache_key, data, WEATHER_CACHE_SECONDS)
    return data
