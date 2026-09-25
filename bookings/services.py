"""Wrappers around the third-party HTTP APIs used by the views.

Every function returns None when the API key is missing or the request fails,
so pages keep rendering without network access.
"""
import os

import requests

TIMEOUT = 5


def _get_json(url, **kwargs):
    try:
        response = requests.get(url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def get_country_activities(country):
    api_key = os.environ.get('RAPIDAPI_KEY')
    if not api_key:
        return None
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "travel-info-api.p.rapidapi.com",
    }
    return _get_json(
        "https://travel-info-api.p.rapidapi.com/country-activities",
        headers=headers,
        params={"country": country},
    )


def get_ip_geolocation_data(ip_address=None):
    api_key = os.environ.get('ABSTRACTAPI_KEY')
    if not api_key:
        return None
    params = {'api_key': api_key}
    # Local addresses can't be geolocated; let the API fall back to the caller's IP.
    if ip_address and not ip_address.startswith(('127.', '10.', '192.168.', '::1')):
        params['ip_address'] = ip_address
    return _get_json('https://ipgeolocation.abstractapi.com/v1/', params=params)


def get_weather_data(city):
    api_key = os.environ.get('WEATHERAPI_KEY')
    if not api_key or not city:
        return None
    return _get_json(
        'https://api.weatherapi.com/v1/current.json',
        params={'key': api_key, 'q': city, 'aqi': 'no'},
    )
