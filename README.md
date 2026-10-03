# JetSet-Journey

A Django travel-booking site for hotels, flights and buses.

## Setup

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Django 4.2 needs Python <= 3.12
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo      # demo hotels, flights and buses
.venv/bin/python manage.py runserver
```

`manage.py` runs with `DJANGO_DEBUG=1` unless you set it yourself. Run the tests with `python manage.py test bookings`.

### Styles

Pages use Tailwind, compiled from `static/src/input.css` into the committed `static/css/app.css`.
After changing classes in templates, rebuild it with the [standalone Tailwind CLI](https://github.com/tailwindlabs/tailwindcss/releases/tag/v3.4.17) (no Node needed):

```bash
curl -sSLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 && chmod +x tailwindcss
./tailwindcss -i static/src/input.css -o static/css/app.css --minify    # add --watch while editing
```

### Production

Served through `config/wsgi.py`, DEBUG is off and these environment variables apply:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required when DEBUG is off |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` (default) redirects HTTP to HTTPS |
| `DJANGO_HSTS_SECONDS` | HSTS max-age; `0` (default) leaves HSTS off |
| `WEATHERAPI_KEY` | Optional; shows weather on hotel results |

Run `python manage.py collectstatic` to gather static files into `staticfiles/`.

## Layout

```
config/      Django project: settings, root URLs, WSGI/ASGI
bookings/    The app: models, views, forms, external API calls, migrations, seed command, tests
templates/   accounts/, hotels/, trips/ (flights + buses), staff/, plus shared pages and partials
static/      css/ (compiled app.css), src/ (Tailwind source) and img/
```
