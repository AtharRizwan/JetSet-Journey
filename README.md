# JetSet-Journey

A Django travel-booking site for hotels, flights and buses.

## Setup

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Django 4.2 needs Python <= 3.12
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo      # demo hotels, flights and buses
.venv/bin/python manage.py runserver
```

Run the tests with `python manage.py test bookings`.

## Layout

```
config/      Django project: settings, root URLs, WSGI/ASGI
bookings/    The app: models, views, forms, external API calls, migrations, seed command, tests
templates/   accounts/, hotels/, trips/ (flights + buses), staff/, plus shared pages and partials
static/      css/ and img/
```
