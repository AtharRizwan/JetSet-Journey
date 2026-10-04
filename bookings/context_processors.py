from urllib.parse import urlencode

from django.urls import reverse


def _tiles(url_name, param, items):
    url = reverse(url_name)
    return [
        {'name': name, 'image': image, 'url': f"{url}?{urlencode({param: value})}"}
        for name, value, image in items
    ]


def popular(request):
    """Image tiles for the "popular ..." sections; each links to a search pre-filled with its value."""
    return {'popular': {
        'destinations': _tiles('search', 'city', [
            ('Paris', 'Paris', 'img/img-1.jpg'),
            ('New York', 'New York', 'img/img-2.jpg'),
            ('London', 'London', 'img/img-3.jpg'),
            ('Amsterdam', 'Amsterdam', 'img/img-4.jpg'),
            ('Sydney', 'Sydney', 'img/img-5.jpg'),
            ('Kyoto', 'Kyoto', 'img/img-6.jpg'),
        ]),
        'hotels': _tiles('search', 'city', [
            ('Pearl Continental, Lahore', 'Lahore', 'img/pc-hotel.jpeg'),
            ('Ramada, Karachi', 'Karachi', 'img/ramada-hotel.jpg'),
            ('Serena, Swat', 'Swat', 'img/serene-hotel.jpeg'),
        ]),
        'airlines': _tiles('search_flights', 'operator', [
            ('PIA', 'PIA', 'img/pia.jpeg'),
            ('AirSial', 'AIRSIAL', 'img/airsial.jpeg'),
            ('AirBlue', 'AIRBLUE', 'img/airblue.jpeg'),
        ]),
        'buses': _tiles('search_buses', 'operator', [
            ('Road Master', 'ROAD MASTER', 'img/bus-road-master.jpeg'),
            ('Faisal Movers', 'FAISAL', 'img/bus-faisal.jpeg'),
            ('Daewoo', 'DAEWOO', 'img/bus-daewoo.jpeg'),
        ]),
    }}
