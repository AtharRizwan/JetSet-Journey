from datetime import date, time, timedelta
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Airline, Bus, BusBooking, BusCompany, Flight, FlightBooking, Hotel, HotelBooking,
    HotelServices, RoomAvailability, Suites,
)

VALID_CARD = {
    'card_holder': 'Test User',
    'card_no': '4242 4242 4242 4242',
    'expiry_date': (date.today() + timedelta(days=365)).isoformat(),
    'cvc': '123',
}


@mock.patch('bookings.views.get_weather_data', return_value=None)
class HotelFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.hotel = Hotel.objects.create(name='Monal', country='Pakistan', city='Islamabad')
        HotelServices.objects.create(hotel=self.hotel, service='Wifi')
        Hotel.objects.create(name='Elsewhere', country='Pakistan', city='Lahore')
        self.suite = Suites.objects.create(name='Deluxe', description='Nice', price_per_night=7000)
        self.check_in = date.today() + timedelta(days=1)
        RoomAvailability.objects.create(name=self.hotel, date=self.check_in)

    def search(self):
        return self.client.post(reverse('search'), {
            'city_country': 'islamabad',
            'check_in_date': self.check_in.isoformat(),
            'check_out_date': (self.check_in + timedelta(days=3)).isoformat(),
        }, follow=True)

    def test_search_returns_hotels_in_city(self, _weather):
        response = self.search()
        self.assertEqual(list(response.context['hotels']), [self.hotel])
        self.assertEqual(response.context['services'], {self.hotel.hotelid: ['Wifi']})

    def test_search_with_invalid_dates_redirects(self, _weather):
        self.client.post(reverse('search'), {
            'city_country': 'Islamabad', 'check_in_date': '2025-01-05', 'check_out_date': '2025-01-01',
        })
        response = self.client.get(reverse('searched_hotels'))
        self.assertRedirects(response, reverse('search'))

    def test_full_booking_creates_hotel_booking(self, _weather):
        self.client.force_login(self.user)
        self.search()
        self.client.get(reverse('booking', args=[self.hotel.hotelid]))
        response = self.client.get(reverse('hotel_summary', args=[self.suite.suiteid]))
        self.assertEqual(response.context['total_cost'], 21000)

        response = self.client.post(reverse('payment'), VALID_CARD)
        self.assertRedirects(response, reverse('my_bookings'))
        booking = HotelBooking.objects.get()
        self.assertEqual((booking.user, booking.hotel, booking.suite_id), (self.user, self.hotel, self.suite))
        self.assertEqual((booking.no_of_days, booking.payment_price), (3, 21000))
        self.assertNotIn('pending_booking', self.client.session)

    def test_invalid_card_creates_no_booking(self, _weather):
        self.client.force_login(self.user)
        self.search()
        self.client.get(reverse('booking', args=[self.hotel.hotelid]))
        self.client.get(reverse('hotel_summary', args=[self.suite.suiteid]))
        response = self.client.post(reverse('payment'), {**VALID_CARD, 'card_no': '1234 5678 9012 3456'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HotelBooking.objects.exists())


class TripFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.other = User.objects.create_user('bob', password='pass12345')
        self.departure = date.today() + timedelta(days=2)
        airline = Airline.objects.create(airline_name='PIA')
        self.flight = Flight.objects.create(
            airline=airline, departure_date=self.departure, departure_time=time(12),
            departure_city='Lahore', destination_city='Karachi', price=10000,
        )
        company = BusCompany.objects.create(company_name='DAEWOO')
        self.bus = Bus.objects.create(
            company=company, departure_date=self.departure, departure_time=time(9),
            departure_city='Lahore', destination_city='Islamabad', price=3000,
        )

    def book(self, url_name, trip_id, seats):
        self.client.post(reverse(url_name, args=[trip_id]), {'seats': seats})
        return self.client.post(reverse('payment'), VALID_CARD)

    def test_flight_search_is_case_insensitive(self):
        self.client.post(reverse('search_flights'), {
            'departure_city': 'lahore', 'destination_city': 'KARACHI',
            'departure_date': self.departure.isoformat(), 'airline_service': 'pia',
        })
        response = self.client.get(reverse('flights_informations'))
        self.assertEqual(list(response.context['flights']), [self.flight])

    def test_bus_search_finds_bus(self):
        self.client.post(reverse('search_buses'), {
            'departure_city': 'Lahore', 'destination_city': 'Islamabad',
            'departure_date': self.departure.isoformat(), 'bus_service': 'daewoo',
        })
        response = self.client.get(reverse('buses_informations'))
        self.assertEqual(list(response.context['buses']), [self.bus])

    def test_flight_booking_saves_seats(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('plane_seat_selection', args=[self.flight.pk]), {'seats': ['3', '4']})
        self.assertRedirects(response, reverse('trip_summary'))
        response = self.client.get(reverse('trip_summary'))
        self.assertEqual(response.context['total'], 20000)

        response = self.client.post(reverse('payment'), VALID_CARD)
        self.assertRedirects(response, reverse('my_bookings'))
        booking = FlightBooking.objects.get()
        self.assertEqual((booking.user, booking.num_seats, booking.payment_price), (self.user, 2, 20000))
        self.assertEqual(sorted(booking.flightbookedseats_set.values_list('seat_no', flat=True)), [3, 4])

        response = self.client.get(reverse('plane_seat_selection', args=[self.flight.pk]))
        booked = [cell['number'] for cell in response.context['seat_cells'] if cell and cell['booked']]
        self.assertEqual(booked, [3, 4])

    def test_bus_booking_saves_seats(self):
        self.client.force_login(self.user)
        self.book('bus_seat_selection', self.bus.pk, ['1'])
        booking = BusBooking.objects.get()
        self.assertEqual((booking.num_seats, booking.payment_price), (1, 3000))
        self.assertEqual(list(booking.busbookedseats_set.values_list('seat_no', flat=True)), [1])

    def test_booked_seat_cannot_be_selected_again(self):
        self.client.force_login(self.user)
        self.book('plane_seat_selection', self.flight.pk, ['5'])

        self.client.force_login(self.other)
        response = self.client.post(reverse('plane_seat_selection', args=[self.flight.pk]), {'seats': ['5']})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('pending_booking', self.client.session)

    def test_seat_taken_before_payment_is_rejected(self):
        other_client = Client()
        other_client.force_login(self.other)
        other_client.post(reverse('plane_seat_selection', args=[self.flight.pk]), {'seats': ['7']})

        self.client.force_login(self.user)
        self.book('plane_seat_selection', self.flight.pk, ['7'])

        response = other_client.post(reverse('payment'), VALID_CARD)
        self.assertRedirects(response, reverse('plane_seat_selection', args=[self.flight.pk]))
        self.assertEqual(FlightBooking.objects.count(), 1)

    def test_out_of_range_seat_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('bus_seat_selection', args=[self.bus.pk]), {'seats': ['21']})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('pending_booking', self.client.session)


class AuthTests(TestCase):
    def test_anonymous_users_are_sent_to_log_in(self):
        for url in (reverse('payment'), reverse('my_bookings'), reverse('booking', args=[1])):
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('log_in')}?next={url}", fetch_redirect_response=False)

    def test_staff_pages_reject_customers(self):
        self.client.force_login(User.objects.create_user('alice', password='pass12345'))
        for url in (reverse('all_users'), reverse('all_bookings'), reverse('add_hotel')):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_staff_can_add_hotel(self):
        self.client.force_login(User.objects.create_user('admin', password='pass12345', is_staff=True))
        self.client.post(reverse('add_hotel'), {
            'name': 'Serena', 'country': 'Pakistan', 'city': 'Swat', 'price_per_night': 9000,
        })
        self.assertTrue(Hotel.objects.filter(name='Serena').exists())

    def test_register_logs_in_and_adds_to_customers(self):
        response = self.client.post(reverse('register'), {
            'username': 'newbie', 'password1': 'a-strong-pass-123', 'password2': 'a-strong-pass-123',
        })
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='newbie')
        self.assertTrue(Group.objects.get(name='customers').user_set.filter(pk=user.pk).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_log_in_follows_next(self):
        User.objects.create_user('alice', password='pass12345')
        response = self.client.post(reverse('log_in'), {
            'username': 'alice', 'password': 'pass12345', 'next': reverse('my_bookings'),
        })
        self.assertRedirects(response, reverse('my_bookings'))

    def test_log_in_ignores_external_next(self):
        User.objects.create_user('alice', password='pass12345')
        response = self.client.post(reverse('log_in'), {
            'username': 'alice', 'password': 'pass12345', 'next': 'https://evil.example.com/',
        })
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_two_profiles_without_phone_numbers(self):
        for name in ('alice', 'bob'):
            self.client.force_login(User.objects.create_user(name, password='pass12345'))
            self.client.post(reverse('change_profile'), {
                'email': f'{name}@example.com', 'first_name': name, 'last_name': 'X',
                'phone_no': '', 'city': 'Lahore', 'country': 'Pakistan', 'address': 'Street 1',
            })
        self.assertEqual(User.objects.filter(user_info__city='Lahore').count(), 2)
