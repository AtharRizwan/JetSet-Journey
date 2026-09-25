from collections import defaultdict
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CustomUserChangeForm, HotelForm, PaymentForm
from .models import Hotel, HotelServices, Suites, User_info, HotelBooking, RoomAvailability
from .models import Flight, FlightBooking, FlightBookedSeats
from .models import Bus, BusBooking, BusBookedSeats
from .services import get_weather_data


# Seat-based trips (flights and buses) share the seat selection, summary and
# payment logic; this table holds what differs between them.
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
    },
}


def trip_operator(kind, trip):
    return trip.airline.airline_name if kind == 'flight' else trip.company.company_name


def booked_seats(kind, trip):
    config = TRIPS[kind]
    lookup = {f"booking_id__{config['booking_field']}": trip}
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
    context = {}
    if request.user.is_authenticated:
        context['first_name'] = request.user.first_name
    return render(request, 'home.html', context)


def search_flights(request):
    if request.method == 'POST':
        request.session['flight_search_params'] = {
            'departure_city': request.POST.get('departure_city', ''),
            'destination_city': request.POST.get('destination_city', ''),
            'departure_date': request.POST.get('departure_date', ''),
            'airline_service': request.POST.get('airline_service', ''),
        }
        return redirect('flights_informations')

    return render(request, 'trips/search_flights.html')


def flights_informations(request):
    params = request.session.get('flight_search_params')
    departure_date = parse_date(params.get('departure_date', '')) if params else None
    if departure_date is None:
        messages.error(request, "Please enter your flight search again.")
        return redirect('search_flights')
    if departure_date < timezone.localdate():
        messages.error(request, "Please choose a departure date that is today or later.")
        return redirect('search_flights')

    departure_city = params.get('departure_city', '').strip()
    destination_city = params.get('destination_city', '').strip()
    airline_service = params.get('airline_service', '').strip()

    flights = Flight.objects.select_related('airline').filter(
        departure_city__iexact=departure_city,
        destination_city__iexact=destination_city,
        departure_date=departure_date,
    ).order_by('departure_time')
    if airline_service:
        flights = flights.filter(airline__airline_name__iexact=airline_service)

    context = {
        'departure_city': departure_city.capitalize(),
        'destination_city': destination_city.capitalize(),
        'departure_date': departure_date,
        'airline_service': airline_service.lower(),
        'flights': flights,
        'count': flights.count(),
    }
    return render(request, 'trips/flights_informations.html', context)


def search_buses(request):
    if request.method == 'POST':
        request.session['bus_search_params'] = {
            'departure_city': request.POST.get('departure_city', ''),
            'destination_city': request.POST.get('destination_city', ''),
            'departure_date': request.POST.get('departure_date', ''),
            'bus_service': request.POST.get('bus_service', ''),
        }
        return redirect('buses_informations')

    return render(request, 'trips/search_buses.html')


def buses_informations(request):
    params = request.session.get('bus_search_params')
    departure_date = parse_date(params.get('departure_date', '')) if params else None
    if departure_date is None:
        messages.error(request, "Please enter your bus search again.")
        return redirect('search_buses')
    if departure_date < timezone.localdate():
        messages.error(request, "Please choose a departure date that is today or later.")
        return redirect('search_buses')

    departure_city = params.get('departure_city', '').strip()
    destination_city = params.get('destination_city', '').strip()
    bus_service = params.get('bus_service', '').strip()

    buses = Bus.objects.select_related('company').filter(
        departure_city__iexact=departure_city,
        destination_city__iexact=destination_city,
        departure_date=departure_date,
    ).order_by('departure_time')
    if bus_service:
        buses = buses.filter(company__company_name__iexact=bus_service)

    context = {
        'departure_city': departure_city.capitalize(),
        'destination_city': destination_city.capitalize(),
        'departure_date': departure_date,
        'bus_service': bus_service.lower(),
        'buses': buses,
        'count': buses.count(),
    }
    return render(request, 'trips/buses_informations.html', context)


def seat_selection(request, kind, id):
    config = TRIPS[kind]
    trip = get_object_or_404(config['model'], pk=id)
    if trip.departure_date < timezone.localdate():
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
                'total': trip.price * len(seats),
            }
            return redirect('trip_summary')

    context = {
        'kind': kind,
        'trip': trip,
        'operator': trip_operator(kind, trip),
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
    if not pending or pending.get('type') not in TRIPS:
        return redirect('home')

    kind = pending['type']
    trip = get_object_or_404(TRIPS[kind]['model'], pk=pending['trip_id'])
    context = {
        'kind': kind,
        'trip': trip,
        'operator': trip_operator(kind, trip),
        'seats': pending['seats'],
        'seat_count': len(pending['seats']),
        'total': pending['total'],
        'seat_url': reverse(TRIPS[kind]['seat_url'], args=[trip.pk]),
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

    return render(request, 'hotels/search.html')


def get_stay_dates(request):
    """Return (check_in, check_out) from the hotel search, or None if they are missing or invalid."""
    params = request.session.get('search_params') or {}
    check_in = parse_date(params.get('check_in_date', '') or '')
    check_out = parse_date(params.get('check_out_date', '') or '')
    if check_in is None or check_out is None or check_out <= check_in or check_in < timezone.localdate():
        return None
    return check_in, check_out


def suite_unavailable(hotel_id, suite_id, check_in, check_out):
    """True if the hotel is closed on any night of the stay or the suite is already booked for an overlapping stay."""
    closed = RoomAvailability.objects.filter(
        name__hotelid=hotel_id, date__gte=check_in, date__lt=check_out, isAvailable=False,
    ).exists()
    overlapping = HotelBooking.objects.filter(
        hotel_id=hotel_id, suite_id_id=suite_id, check_in__lt=check_out, check_out__gt=check_in,
    ).exists()
    return closed or overlapping


def searched_hotels(request):
    stay = get_stay_dates(request)
    if stay is None:
        messages.error(request, "Please choose a check-in date from today onwards and a check-out date after it.")
        return redirect('search')

    city = request.session['search_params'].get('city_country', '').strip()
    hotels = Hotel.objects.filter(
        city__iexact=city,
        roomavailability__date__range=stay,
        roomavailability__isAvailable=True,
    ).distinct()

    services = defaultdict(list)
    for hotel_service in HotelServices.objects.filter(hotel__in=hotels):
        services[hotel_service.hotel_id].append(hotel_service.service)

    context = {
        'city_country': city.capitalize(),
        'check_in_date': stay[0],
        'check_out_date': stay[1],
        'hotels': hotels,
        'count': hotels.count(),
        'weather_data': get_weather_data(city),
        'services': dict(services),
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
    hotel = get_object_or_404(Hotel, hotelid=id)
    context = {
        'req_hotel': [hotel],
    }
    return render(request, 'hotels/hotel_details.html', context)


@login_required
def booking(request, id):
    hotel = get_object_or_404(Hotel, hotelid=id)
    request.session['hotel_booked'] = hotel.hotelid

    context = {
        'hotel': hotel,
        'suites': Suites.objects.all(),
    }
    return render(request, 'hotels/booking.html', context)


@login_required
def hotel_summary(request, id):
    suite = get_object_or_404(Suites, suiteid=id)
    hotel_id = request.session.get('hotel_booked')
    stay = get_stay_dates(request)
    if hotel_id is None or stay is None:
        messages.error(request, "Please search for a hotel first.")
        return redirect('search')

    hotel = get_object_or_404(Hotel, hotelid=hotel_id)
    if suite_unavailable(hotel.hotelid, suite.suiteid, *stay):
        messages.error(request, f"The {suite.name} at {hotel.name} is not available for those dates.")
        return redirect('booking', id=hotel.hotelid)

    no_of_days = (stay[1] - stay[0]).days
    total_cost = suite.price_per_night * no_of_days
    request.session['pending_booking'] = {
        'type': 'hotel',
        'hotel_id': hotel.hotelid,
        'suite_id': suite.suiteid,
        'check_in': stay[0].isoformat(),
        'check_out': stay[1].isoformat(),
        'no_of_days': no_of_days,
        'total': total_cost,
    }

    context = {
        'hotel': hotel,
        'suite': suite,
        'check_in_date': stay[0],
        'check_out_date': stay[1],
        'no_of_days': no_of_days,
        'total_cost': total_cost,
    }
    return render(request, 'hotels/hotel_summary.html', context)


def describe_pending_booking(pending):
    if pending['type'] == 'hotel':
        hotel = get_object_or_404(Hotel, hotelid=pending['hotel_id'])
        suite = get_object_or_404(Suites, suiteid=pending['suite_id'])
        return f"{suite.name} at {hotel.name}, {pending['check_in']} to {pending['check_out']} ({pending['no_of_days']} night(s))"

    trip = get_object_or_404(TRIPS[pending['type']]['model'], pk=pending['trip_id'])
    seats = ', '.join(str(seat) for seat in pending['seats'])
    return f"{trip_operator(pending['type'], trip)} {trip} on {trip.departure_date}, seat(s) {seats}"


@login_required
def payment(request):
    pending = request.session.get('pending_booking')
    if not pending:
        messages.error(request, "There is nothing to pay for yet.")
        return redirect('home')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            if pending['type'] == 'hotel':
                check_in, check_out = parse_date(pending['check_in']), parse_date(pending['check_out'])
                with transaction.atomic():
                    if suite_unavailable(pending['hotel_id'], pending['suite_id'], check_in, check_out):
                        del request.session['pending_booking']
                        messages.error(request, "Sorry, that suite was just booked for those dates. Please choose again.")
                        return redirect('booking', id=pending['hotel_id'])

                    HotelBooking.objects.create(
                        user=request.user,
                        hotel_id=pending['hotel_id'],
                        suite_id_id=pending['suite_id'],
                        check_in=check_in,
                        check_out=check_out,
                        no_of_days=pending['no_of_days'],
                        payment_price=pending['total'],
                    )
            else:
                config = TRIPS[pending['type']]
                trip = get_object_or_404(config['model'], pk=pending['trip_id'])
                with transaction.atomic():
                    if booked_seats(pending['type'], trip) & set(pending['seats']):
                        del request.session['pending_booking']
                        messages.error(request, "Sorry, some of your seats were just booked by someone else. Please choose again.")
                        return redirect(config['seat_url'], id=trip.pk)

                    trip_booking = config['booking_model'].objects.create(
                        user=request.user,
                        num_seats=len(pending['seats']),
                        payment_price=pending['total'],
                        **{config['booking_field']: trip},
                    )
                    config['seat_model'].objects.bulk_create(
                        config['seat_model'](booking_id=trip_booking, seat_no=seat)
                        for seat in pending['seats']
                    )

            del request.session['pending_booking']
            messages.success(request, "Payment successful! Your booking is confirmed.")
            return redirect('my_bookings')

        messages.error(request, "Payment form is invalid. Please check the entered information.")
    else:
        form = PaymentForm()

    context = {
        'form': form,
        'description': describe_pending_booking(pending),
        'total': pending['total'],
    }
    return render(request, 'payment.html', context)


@login_required
def my_bookings(request):
    context = {
        'hotel_bookings': HotelBooking.objects.filter(user=request.user)
            .select_related('hotel', 'suite_id').order_by('-id'),
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
            group, _ = Group.objects.get_or_create(name='customers')
            group.user_set.add(user)
            login(request, user)
            messages.success(request, "Welcome to Jet-Set Journey!")
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
            messages.success(request, "Your profile has been updated")
    else:
        user_info = User_info.objects.filter(user=request.user).first()
        form = CustomUserChangeForm(instance=request.user, initial={
            'city': user_info.city if user_info else '',
            'country': user_info.country if user_info else '',
            'phone_no': (user_info.phone_no or '') if user_info else '',
            'address': user_info.address if user_info else '',
        })

    context = {
        'form': form,
        'username': request.user.first_name,
    }
    return render(request, 'accounts/change_profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {
        'form': form
    })


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

        messages.error(request, 'Invalid Username or Password.')
        login_url = reverse('log_in')
        if next_url:
            login_url += '?' + urlencode({'next': next_url})
        return redirect(login_url)

    return render(request, 'accounts/log_in.html', {'next': next_url})


def log_out(request):
    logout(request)
    return redirect('home')


@staff_member_required(login_url='log_in')
def all_users(request):
    all_users_info = User_info.objects.select_related('user')
    context = {
        'all_users_info': all_users_info
    }
    return render(request, 'staff/all_users.html', context)


@staff_member_required(login_url='log_in')
def all_bookings(request):
    context = {
        'hotel_bookings': HotelBooking.objects.select_related('hotel', 'user', 'suite_id').order_by('-id'),
        'flight_bookings': FlightBooking.objects.select_related('user', 'flight__airline')
            .prefetch_related('flightbookedseats_set').order_by('-booking_id'),
        'bus_bookings': BusBooking.objects.select_related('user', 'bus__company')
            .prefetch_related('busbookedseats_set').order_by('-booking_id'),
    }
    return render(request, 'staff/all_bookings.html', context)


def aboutus(request):
    return render(request, 'aboutus.html')
