import secrets
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles import finders
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .forms import CustomUserChangeForm, HotelForm, PaymentForm
from .models import Hotel, Suites, User_info, HotelBooking, RoomAvailability
from .models import Airline, Flight, FlightBooking, FlightBookedSeats
from .models import Bus, BusCompany, BusBooking, BusBookedSeats
from .services import get_weather_data


# Seat-based trips (flights and buses) share the search, seat selection, summary
# and payment logic; this table holds what differs between them.
TRIPS = {
    'flight': {
        'model': Flight,
        'seat_count': 40,
        'booking_model': FlightBooking,
        'booking_field': 'flight',
        'seat_model': FlightBookedSeats,
        'seat_url': 'plane_seat_selection',
        'template': 'trips/plane_seat_selection.html',
        'search_url': 'search_flights',
        'search_template': 'trips/search_flights.html',
        'results_url': 'flights_informations',
        'results_template': 'trips/flights_informations.html',
        'results_name': 'flights',
        'session_key': 'flight_search_params',
        'service_param': 'airline_service',
        'operator_model': Airline,
        'operator_field': 'airline__airline_name',
        'logo': 'img/{}.jpeg',
    },
    'bus': {
        'model': Bus,
        'seat_count': 20,
        'booking_model': BusBooking,
        'booking_field': 'bus',
        'seat_model': BusBookedSeats,
        'seat_url': 'bus_seat_selection',
        'template': 'trips/bus_seat_selection.html',
        'search_url': 'search_buses',
        'search_template': 'trips/search_buses.html',
        'results_url': 'buses_informations',
        'results_template': 'trips/buses_informations.html',
        'results_name': 'buses',
        'session_key': 'bus_search_params',
        'service_param': 'bus_service',
        'operator_model': BusCompany,
        'operator_field': 'company__company_name',
        'logo': 'img/bus-{}.jpeg',
    },
}

FALLBACK_LOGO = 'img/logo2.png'

# Suite and hotel photos are picked by a keyword in the name.
SUITE_IMAGES = {
    'twin': 'img/hotel-room-twin-bed.jpg',
    'platinum': 'img/hotel-room-platinum.jpg',
    'presidential': 'img/hotel-room-presidential.jpg',
}
HOTEL_IMAGES = {
    'pearl': 'img/pc-hotel.jpeg',
    'ramada': 'img/ramada-hotel.jpg',
    'serena': 'img/serene-hotel.jpeg',
}


def image_for(name, images, default):
    lowered = name.lower()
    return next((path for keyword, path in images.items() if keyword in lowered), default)


@lru_cache(maxsize=None)
def operator_logo(kind, name):
    """Static path of the airline/bus-company logo, or the site logo if there is no matching image."""
    path = TRIPS[kind]['logo'].format(slugify(name))
    return path if finders.find(path) else FALLBACK_LOGO


def trip_operator(kind, trip):
    return trip.airline.airline_name if kind == 'flight' else trip.company.company_name


def trip_departed(trip):
    departure = timezone.make_aware(datetime.combine(trip.departure_date, trip.departure_time))
    return departure <= timezone.now()


def booked_seats(kind, trip):
    config = TRIPS[kind]
    lookup = {config['booking_field']: trip}
    return set(config['seat_model'].objects.filter(**lookup).values_list('seat_no', flat=True))


def seat_layout(seat_count, taken):
    """Cells for the seat grid, filled column by column: two seats, an aisle, two seats."""
    cells = []
    for first in range(1, seat_count + 1, 4):
        column = [n for n in range(first, first + 4) if n <= seat_count]
        for i, number in enumerate(column):
            if i == 2:
                cells.append(None)
            cells.append({'number': number, 'booked': number in taken})
    return cells


def home(request):
    return render(request, 'home.html')


def trip_search(request, kind):
    config = TRIPS[kind]
    if request.method == 'POST':
        request.session[config['session_key']] = {
            'departure_city': request.POST.get('departure_city', ''),
            'destination_city': request.POST.get('destination_city', ''),
            'departure_date': request.POST.get('departure_date', ''),
            config['service_param']: request.POST.get(config['service_param'], ''),
        }
        return redirect(config['results_url'])

    operator_name = config['operator_field'].split('__')[1]
    context = {
        'operators': config['operator_model'].objects.order_by(operator_name)
            .values_list(operator_name, flat=True).distinct(),
        'selected_operator': request.GET.get('operator', ''),
    }
    return render(request, config['search_template'], context)


def trip_results(request, kind):
    config = TRIPS[kind]
    label = 'flight' if kind == 'flight' else 'bus'
    params = request.session.get(config['session_key'])
    departure_date = parse_date(params.get('departure_date', '') or '') if params else None
    if departure_date is None:
        messages.error(request, f"Please enter your {label} search again.")
        return redirect(config['search_url'])
    today = timezone.localdate()
    if departure_date < today:
        messages.error(request, "Please choose a departure date that is today or later.")
        return redirect(config['search_url'])

    departure_city = params.get('departure_city', '').strip()
    destination_city = params.get('destination_city', '').strip()
    service = params.get(config['service_param'], '').strip()

    trips = config['model'].objects.select_related(config['operator_field'].split('__')[0]).filter(
        departure_city__iexact=departure_city,
        destination_city__iexact=destination_city,
        departure_date=departure_date,
    ).order_by('departure_time')
    if departure_date == today:
        trips = trips.filter(departure_time__gt=timezone.localtime().time())
    if service:
        trips = trips.filter(**{f"{config['operator_field']}__iexact": service})

    trips = list(trips)
    for trip in trips:
        trip.operator = trip_operator(kind, trip)
        trip.logo = operator_logo(kind, trip.operator)

    context = {
        'departure_city': departure_city.title(),
        'destination_city': destination_city.title(),
        'departure_date': departure_date,
        'service': service,
        config['results_name']: trips,
        'count': len(trips),
    }
    return render(request, config['results_template'], context)


def search_flights(request):
    return trip_search(request, 'flight')


def flights_informations(request):
    return trip_results(request, 'flight')


def search_buses(request):
    return trip_search(request, 'bus')


def buses_informations(request):
    return trip_results(request, 'bus')


def seat_selection(request, kind, id):
    config = TRIPS[kind]
    trip = get_object_or_404(config['model'], pk=id)
    if trip_departed(trip):
        messages.error(request, "This trip has already departed.")
        return redirect(config['search_url'])
    taken = booked_seats(kind, trip)

    if request.method == 'POST':
        try:
            seats = sorted({int(seat) for seat in request.POST.getlist('seats')})
        except ValueError:
            seats = []

        if not seats:
            messages.error(request, "Please select at least one seat.")
        elif any(seat < 1 or seat > config['seat_count'] or seat in taken for seat in seats):
            messages.error(request, "Some of the selected seats are no longer available.")
        else:
            request.session['pending_booking'] = {
                'type': kind,
                'trip_id': trip.pk,
                'seats': seats,
                'token': secrets.token_urlsafe(16),
            }
            return redirect('trip_summary')

    operator = trip_operator(kind, trip)
    context = {
        'kind': kind,
        'trip': trip,
        'operator': operator,
        'logo': operator_logo(kind, operator),
        'seat_cells': seat_layout(config['seat_count'], taken),
    }
    return render(request, config['template'], context)


@login_required
def plane_seat_selection(request, id):
    return seat_selection(request, 'flight', id)


@login_required
def bus_seat_selection(request, id):
    return seat_selection(request, 'bus', id)


@login_required
def trip_summary(request):
    pending = request.session.get('pending_booking')
    booking = load_pending_booking(pending)
    if booking is None or booking['type'] == 'hotel':
        return redirect('home')

    kind, trip = booking['type'], booking['trip']
    config = TRIPS[kind]
    if trip_departed(trip):
        del request.session['pending_booking']
        messages.error(request, "This trip has already departed.")
        return redirect(config['search_url'])
    if booked_seats(kind, trip) & set(booking['seats']):
        del request.session['pending_booking']
        messages.error(request, "Some of your seats were just booked by someone else. Please choose again.")
        return redirect(config['seat_url'], id=trip.pk)

    context = {
        'kind': kind,
        'trip': trip,
        'operator': booking['operator'],
        'logo': operator_logo(kind, booking['operator']),
        'seats': booking['seats'],
        'seat_count': len(booking['seats']),
        'total': booking['total'],
        'seat_url': reverse(config['seat_url'], args=[trip.pk]),
    }
    return render(request, 'trips/trip_summary.html', context)


def search(request):
    if request.method == 'POST':
        request.session['search_params'] = {
            'city_country': request.POST.get('city_country', ''),
            'check_in_date': request.POST.get('check_in_date', ''),
            'check_out_date': request.POST.get('check_out_date', ''),
        }
        return redirect('searched_hotels')

    return render(request, 'hotels/search.html', {'city': request.GET.get('city', '')})


def get_stay_dates(request):
    """Return (check_in, check_out) from the hotel search, or None if they are missing or invalid."""
    params = request.session.get('search_params') or {}
    check_in = parse_date(params.get('check_in_date', '') or '')
    check_out = parse_date(params.get('check_out_date', '') or '')
    if check_in is None or check_out is None or check_out <= check_in or check_in < timezone.localdate():
        return None
    return check_in, check_out


def open_for_stay(hotels, check_in, check_out):
    """Hotels from the queryset with an open availability row for every night of the stay."""
    nights = (check_out - check_in).days
    open_nights = Count('roomavailability', filter=Q(
        roomavailability__date__gte=check_in,
        roomavailability__date__lt=check_out,
        roomavailability__is_available=True,
    ))
    return hotels.annotate(open_nights=open_nights).filter(open_nights=nights)


def booked_suite_ids(hotel_id, check_in, check_out):
    """Suites already booked at the hotel for a stay overlapping the given dates."""
    return set(HotelBooking.objects.filter(
        hotel_id=hotel_id, check_in__lt=check_out, check_out__gt=check_in,
    ).values_list('suite_id', flat=True))


def stay_unavailable(hotel_id, suite_id, check_in, check_out):
    """True if the hotel isn't open every night of the stay or the suite is already booked for an overlapping stay."""
    hotel_open = open_for_stay(Hotel.objects.filter(hotelid=hotel_id), check_in, check_out).exists()
    return not hotel_open or suite_id in booked_suite_ids(hotel_id, check_in, check_out)


def stay_total(hotel, suite, nights):
    return nights * (hotel.price_per_night + suite.price_per_night)


def searched_hotels(request):
    stay = get_stay_dates(request)
    if stay is None:
        messages.error(request, "Please choose a check-in date from today onwards and a check-out date after it.")
        return redirect('search')

    city = request.session['search_params'].get('city_country', '').strip()
    hotels = list(
        open_for_stay(Hotel.objects.filter(city__iexact=city), *stay)
        .prefetch_related('hotelservices_set').order_by('name')
    )
    for hotel in hotels:
        hotel.image = image_for(hotel.name, HOTEL_IMAGES, 'img/cover_bg_1.jpg')

    context = {
        'city_country': city.title(),
        'check_in_date': stay[0],
        'check_out_date': stay[1],
        'no_of_days': (stay[1] - stay[0]).days,
        'hotels': hotels,
        'count': len(hotels),
        'weather_data': get_weather_data(city),
    }
    return render(request, 'hotels/searched_hotels.html', context)


@staff_member_required(login_url='log_in')
def add_hotel(request):
    if request.method == 'POST':
        form = HotelForm(request.POST)
        if form.is_valid():
            hotel = form.save()
            messages.success(request, f"{hotel.name} has been added.")
            return redirect('add_hotel')
    else:
        form = HotelForm()

    return render(request, 'hotels/add_hotel.html', {'form': form})


def hotel_details(request, id):
    hotel = get_object_or_404(Hotel.objects.prefetch_related('hotelservices_set'), hotelid=id)
    hotel.image = image_for(hotel.name, HOTEL_IMAGES, 'img/cover_bg_1.jpg')
    return render(request, 'hotels/hotel_details.html', {'hotel': hotel})


@login_required
def booking(request, id):
    hotel = get_object_or_404(Hotel, hotelid=id)
    stay = get_stay_dates(request)
    if stay is None:
        messages.error(request, "Please search for your stay dates first.")
        return redirect('search')
    if not open_for_stay(Hotel.objects.filter(hotelid=hotel.hotelid), *stay).exists():
        messages.error(request, f"{hotel.name} is not open for all of those dates.")
        return redirect('searched_hotels')

    nights = (stay[1] - stay[0]).days
    taken = booked_suite_ids(hotel.hotelid, *stay)
    suites = list(Suites.objects.order_by('price_per_night'))
    for suite in suites:
        suite.image = image_for(suite.name, SUITE_IMAGES, 'img/hotel-room-deluxe.jpg')
        suite.nightly_price = hotel.price_per_night + suite.price_per_night
        suite.total = stay_total(hotel, suite, nights)
        suite.unavailable = suite.suiteid in taken

    context = {
        'hotel': hotel,
        'suites': suites,
        'check_in_date': stay[0],
        'check_out_date': stay[1],
        'no_of_days': nights,
    }
    return render(request, 'hotels/booking.html', context)


@login_required
def hotel_summary(request, hotel_id, suite_id):
    hotel = get_object_or_404(Hotel, hotelid=hotel_id)
    suite = get_object_or_404(Suites, suiteid=suite_id)
    stay = get_stay_dates(request)
    if stay is None:
        messages.error(request, "Please search for a hotel first.")
        return redirect('search')

    if stay_unavailable(hotel.hotelid, suite.suiteid, *stay):
        messages.error(request, f"The {suite.name} at {hotel.name} is not available for those dates.")
        return redirect('booking', id=hotel.hotelid)

    no_of_days = (stay[1] - stay[0]).days
    request.session['pending_booking'] = {
        'type': 'hotel',
        'hotel_id': hotel.hotelid,
        'suite_id': suite.suiteid,
        'check_in': stay[0].isoformat(),
        'check_out': stay[1].isoformat(),
        'token': secrets.token_urlsafe(16),
    }
    suite.image = image_for(suite.name, SUITE_IMAGES, 'img/hotel-room-deluxe.jpg')

    context = {
        'hotel': hotel,
        'suite': suite,
        'check_in_date': stay[0],
        'check_out_date': stay[1],
        'no_of_days': no_of_days,
        'nightly_price': hotel.price_per_night + suite.price_per_night,
        'total_cost': stay_total(hotel, suite, no_of_days),
    }
    return render(request, 'hotels/hotel_summary.html', context)


def load_pending_booking(pending):
    """Resolve the session's pending booking against the database, with prices recalculated.

    Returns None if it is missing, malformed, or refers to something that no longer exists.
    """
    if not isinstance(pending, dict) or not pending.get('token'):
        return None
    try:
        if pending['type'] == 'hotel':
            hotel = Hotel.objects.get(hotelid=pending['hotel_id'])
            suite = Suites.objects.get(suiteid=pending['suite_id'])
            check_in, check_out = parse_date(pending['check_in']), parse_date(pending['check_out'])
            if check_in is None or check_out is None or check_out <= check_in:
                return None
            nights = (check_out - check_in).days
            return {
                'type': 'hotel', 'hotel': hotel, 'suite': suite,
                'check_in': check_in, 'check_out': check_out, 'no_of_days': nights,
                'total': stay_total(hotel, suite, nights),
                'description': f"{suite.name} at {hotel.name}, {check_in:%d %b %Y} to {check_out:%d %b %Y} "
                               f"({nights} night{'s' if nights != 1 else ''})",
                'back_url': reverse('booking', args=[hotel.hotelid]),
            }

        config = TRIPS[pending['type']]
        trip = config['model'].objects.get(pk=pending['trip_id'])
        seats = [int(seat) for seat in pending['seats']]
        if not seats:
            return None
        operator = trip_operator(pending['type'], trip)
        return {
            'type': pending['type'], 'trip': trip, 'seats': seats, 'operator': operator,
            'total': trip.price * len(seats),
            'description': f"{operator} {trip} on {trip.departure_date:%d %b %Y}, "
                           f"seat{'s' if len(seats) != 1 else ''} {', '.join(map(str, seats))}",
            'back_url': reverse('trip_summary'),
        }
    except (KeyError, TypeError, ValueError, Hotel.DoesNotExist, Suites.DoesNotExist,
            Flight.DoesNotExist, Bus.DoesNotExist):
        return None


def complete_hotel_booking(request, booking):
    """Create the hotel booking, or return a redirect if the stay can no longer be booked."""
    hotel, suite = booking['hotel'], booking['suite']
    if booking['check_in'] < timezone.localdate():
        messages.error(request, "Your check-in date has passed. Please search again.")
        return redirect('search')
    with transaction.atomic():
        Hotel.objects.select_for_update().get(pk=hotel.pk)
        if stay_unavailable(hotel.hotelid, suite.suiteid, booking['check_in'], booking['check_out']):
            messages.error(request, "Sorry, that suite was just booked for those dates. Please choose again.")
            return redirect('booking', id=hotel.hotelid)
        HotelBooking.objects.create(
            user=request.user,
            hotel=hotel,
            suite=suite,
            check_in=booking['check_in'],
            check_out=booking['check_out'],
            no_of_days=booking['no_of_days'],
            payment_price=booking['total'],
        )
    return None


def complete_trip_booking(request, booking):
    """Create the flight/bus booking and its seats, or return a redirect if they can no longer be booked."""
    kind, trip, seats = booking['type'], booking['trip'], booking['seats']
    config = TRIPS[kind]
    if trip_departed(trip):
        messages.error(request, "This trip has already departed.")
        return redirect(config['search_url'])
    taken_message = "Sorry, some of your seats were just booked by someone else. Please choose again."
    try:
        with transaction.atomic():
            config['model'].objects.select_for_update().get(pk=trip.pk)
            if booked_seats(kind, trip) & set(seats):
                messages.error(request, taken_message)
                return redirect(config['seat_url'], id=trip.pk)
            trip_booking = config['booking_model'].objects.create(
                user=request.user,
                num_seats=len(seats),
                payment_price=booking['total'],
                **{config['booking_field']: trip},
            )
            config['seat_model'].objects.bulk_create(
                config['seat_model'](booking=trip_booking, seat_no=seat, **{config['booking_field']: trip})
                for seat in seats
            )
    except IntegrityError:
        # Another payment took one of the seats between our check and the insert.
        messages.error(request, taken_message)
        return redirect(config['seat_url'], id=trip.pk)
    return None


@login_required
def payment(request):
    pending = request.session.get('pending_booking')
    booking = load_pending_booking(pending)
    if booking is None:
        request.session.pop('pending_booking', None)
        messages.error(request, "There is nothing to pay for yet.")
        return redirect('home')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if request.POST.get('token') != pending['token']:
            # The pending booking was replaced (e.g. in another tab) after this payment page was shown.
            messages.error(request, "Your booking changed in another tab. Please check the details below and pay again.")
            return redirect('payment')
        if form.is_valid():
            if booking['type'] == 'hotel':
                failed = complete_hotel_booking(request, booking)
            else:
                failed = complete_trip_booking(request, booking)
            del request.session['pending_booking']
            if failed:
                return failed
            messages.success(request, "Payment successful! Your booking is confirmed.")
            return redirect('my_bookings')

        messages.error(request, "Payment form is invalid. Please check the entered information.")
    else:
        form = PaymentForm()

    context = {
        'form': form,
        'description': booking['description'],
        'total': booking['total'],
        'token': pending['token'],
        'back_url': booking['back_url'],
    }
    return render(request, 'payment.html', context)


@login_required
def my_bookings(request):
    context = {
        'hotel_bookings': HotelBooking.objects.filter(user=request.user)
            .select_related('hotel', 'suite').order_by('-id'),
        'flight_bookings': FlightBooking.objects.filter(user=request.user)
            .select_related('flight__airline').prefetch_related('flightbookedseats_set')
            .order_by('-booking_id'),
        'bus_bookings': BusBooking.objects.filter(user=request.user)
            .select_related('bus__company').prefetch_related('busbookedseats_set')
            .order_by('-booking_id'),
    }
    return render(request, 'accounts/my_bookings.html', context)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            User_info.objects.create(user=user)
            group, _ = Group.objects.get_or_create(name='customers')
            group.user_set.add(user)
            login(request, user)
            messages.success(request, "Welcome to JetSet Journey!")
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def change_profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('change_profile')
    else:
        form = CustomUserChangeForm(instance=request.user)

    return render(request, 'accounts/change_profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change_password')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


def log_in(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = ''

    if request.method == "POST":
        username = request.POST.get("username", '')
        password = request.POST.get("password", '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or 'home')

        messages.error(request, 'Invalid username or password.')
        login_url = reverse('log_in')
        if next_url:
            login_url += '?' + urlencode({'next': next_url})
        return redirect(login_url)

    return render(request, 'accounts/log_in.html', {'next': next_url})


@require_POST
def log_out(request):
    logout(request)
    return redirect('home')


@staff_member_required(login_url='log_in')
def all_users(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'staff/all_users.html', {'users': users})


@staff_member_required(login_url='log_in')
def all_bookings(request):
    context = {
        'hotel_bookings': HotelBooking.objects.select_related('hotel', 'user', 'suite').order_by('-id'),
        'flight_bookings': FlightBooking.objects.select_related('user', 'flight__airline')
            .prefetch_related('flightbookedseats_set').order_by('-booking_id'),
        'bus_bookings': BusBooking.objects.select_related('user', 'bus__company')
            .prefetch_related('busbookedseats_set').order_by('-booking_id'),
    }
    return render(request, 'staff/all_bookings.html', context)


def aboutus(request):
    return render(request, 'aboutus.html')
