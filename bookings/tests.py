from datetime import time, timedelta
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Airline, Bus, BusBooking, BusCompany, Flight, FlightBookedSeats, FlightBooking, Hotel, HotelBooking,
    HotelServices, RoomAvailability, Suites, User_info,
)

TODAY = timezone.localdate()

VALID_CARD = {
    'card_holder': 'Test User',
    'card_no': '4242 4242 4242 4242',
    'expiry': (TODAY + timedelta(days=365)).strftime('%m/%y'),
    'cvc': '123',
}


def pay(client, card=VALID_CARD):
    """Submit the payment form the way the browser does, including the page's token."""
    token = client.session.get('pending_booking', {}).get('token', '')
    return client.post(reverse('payment'), {**card, 'token': token})


@mock.patch('bookings.views.get_weather_data', return_value=None)
class HotelFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.hotel = Hotel.objects.create(name='Monal', country='Pakistan', city='Islamabad')
        HotelServices.objects.create(hotel=self.hotel, service='Wifi')
        Hotel.objects.create(name='Elsewhere', country='Pakistan', city='Lahore')
        self.suite = Suites.objects.create(name='Deluxe', description='Nice', price_per_night=7000)
        self.check_in = TODAY + timedelta(days=1)
        for n in range(3):
            RoomAvailability.objects.create(hotel=self.hotel, date=self.check_in + timedelta(days=n))

    def summary_url(self, hotel=None):
        return reverse('hotel_summary', args=[(hotel or self.hotel).hotelid, self.suite.suiteid])

    def search(self):
        return self.client.post(reverse('search'), {
            'city_country': 'islamabad',
            'check_in_date': self.check_in.isoformat(),
            'check_out_date': (self.check_in + timedelta(days=3)).isoformat(),
        }, follow=True)

    def test_search_returns_hotels_in_city(self, _weather):
        response = self.search()
        self.assertEqual(list(response.context['hotels']), [self.hotel])
        self.assertContains(response, 'Wifi')

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
        response = self.client.get(self.summary_url())
        # 3 nights x (hotel 100 + suite 7000)
        self.assertEqual(response.context['total_cost'], 21300)

        response = pay(self.client)
        self.assertRedirects(response, reverse('my_bookings'))
        booking = HotelBooking.objects.get()
        self.assertEqual((booking.user, booking.hotel, booking.suite), (self.user, self.hotel, self.suite))
        self.assertEqual((booking.no_of_days, booking.payment_price), (3, 21300))
        self.assertEqual((booking.check_in, booking.check_out), (self.check_in, self.check_in + timedelta(days=3)))
        self.assertNotIn('pending_booking', self.client.session)

    def test_suite_cannot_be_booked_twice_for_overlapping_dates(self, _weather):
        other = User.objects.create_user('bob', password='pass12345')
        other_client = Client()
        other_client.force_login(other)
        for client in (self.client, other_client):
            client.force_login(self.user if client is self.client else other)
            client.post(reverse('search'), {
                'city_country': 'islamabad',
                'check_in_date': self.check_in.isoformat(),
                'check_out_date': (self.check_in + timedelta(days=3)).isoformat(),
            })
            client.get(reverse('booking', args=[self.hotel.hotelid]))
            client.get(self.summary_url())

        pay(self.client)
        response = pay(other_client)
        self.assertRedirects(response, reverse('booking', args=[self.hotel.hotelid]))
        self.assertEqual(HotelBooking.objects.count(), 1)

        response = other_client.get(self.summary_url())
        self.assertRedirects(response, reverse('booking', args=[self.hotel.hotelid]))

    def test_closed_dates_block_booking(self, _weather):
        RoomAvailability.objects.filter(date=self.check_in + timedelta(days=1)).update(is_available=False)
        self.client.force_login(self.user)
        self.search()
        self.client.get(reverse('booking', args=[self.hotel.hotelid]))
        response = self.client.get(self.summary_url())
        self.assertRedirects(response, reverse('booking', args=[self.hotel.hotelid]), fetch_redirect_response=False)
        self.assertNotIn('pending_booking', self.client.session)

    def test_invalid_card_creates_no_booking(self, _weather):
        self.client.force_login(self.user)
        self.search()
        self.client.get(reverse('booking', args=[self.hotel.hotelid]))
        self.client.get(self.summary_url())
        response = pay(self.client, {**VALID_CARD, 'card_no': '1234 5678 9012 3456'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HotelBooking.objects.exists())


class TripFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.other = User.objects.create_user('bob', password='pass12345')
        self.departure = TODAY + timedelta(days=2)
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
        return pay(self.client)

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

        response = pay(self.client)
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

        response = pay(other_client)
        self.assertRedirects(response, reverse('plane_seat_selection', args=[self.flight.pk]))
        self.assertEqual(FlightBooking.objects.count(), 1)

    def test_past_flight_search_is_rejected(self):
        self.client.post(reverse('search_flights'), {
            'departure_city': 'Lahore', 'destination_city': 'Karachi',
            'departure_date': (TODAY - timedelta(days=1)).isoformat(),
        })
        response = self.client.get(reverse('flights_informations'))
        self.assertRedirects(response, reverse('search_flights'))

    def test_departed_bus_cannot_be_booked(self):
        self.bus.departure_date = TODAY - timedelta(days=1)
        self.bus.save()
        self.client.force_login(self.user)
        response = self.client.post(reverse('bus_seat_selection', args=[self.bus.pk]), {'seats': ['1']})
        self.assertRedirects(response, reverse('search_buses'))
        self.assertNotIn('pending_booking', self.client.session)

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

    def test_staff_all_bookings_lists_every_kind(self):
        self.client.force_login(User.objects.create_user('admin', password='pass12345', is_staff=True))
        response = self.client.get(reverse('all_bookings'))
        for key in ('hotel_bookings', 'flight_bookings', 'bus_bookings'):
            self.assertIn(key, response.context)

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
        self.assertEqual(User.objects.filter(profile__city='Lahore').count(), 2)


@mock.patch('bookings.views.get_weather_data', return_value=None)
class HotelAvailabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        self.client.force_login(self.user)
        self.hotel = Hotel.objects.create(name='Monal', country='Pakistan', city='Islamabad', price_per_night=1000)
        self.other_hotel = Hotel.objects.create(name='Serena', country='Pakistan', city='Islamabad', price_per_night=2000)
        self.suite = Suites.objects.create(name='Deluxe', description='Nice', price_per_night=7000)
        self.check_in = TODAY + timedelta(days=1)
        for hotel in (self.hotel, self.other_hotel):
            for n in range(3):
                RoomAvailability.objects.create(hotel=hotel, date=self.check_in + timedelta(days=n))
        self.client.post(reverse('search'), {
            'city_country': 'Islamabad',
            'check_in_date': self.check_in.isoformat(),
            'check_out_date': (self.check_in + timedelta(days=3)).isoformat(),
        })

    def summary_url(self, hotel):
        return reverse('hotel_summary', args=[hotel.hotelid, self.suite.suiteid])

    def test_hotel_missing_a_night_is_not_listed_or_bookable(self, _weather):
        RoomAvailability.objects.filter(hotel=self.hotel, date=self.check_in + timedelta(days=2)).delete()
        response = self.client.get(reverse('searched_hotels'))
        self.assertEqual(list(response.context['hotels']), [self.other_hotel])
        self.assertRedirects(self.client.get(reverse('booking', args=[self.hotel.hotelid])), reverse('searched_hotels'))
        response = self.client.get(self.summary_url(self.hotel))
        self.assertRedirects(response, reverse('booking', args=[self.hotel.hotelid]), fetch_redirect_response=False)

    def test_hotel_closed_after_summary_is_rejected_at_payment(self, _weather):
        self.client.get(self.summary_url(self.hotel))
        RoomAvailability.objects.filter(hotel=self.hotel, date=self.check_in).update(is_available=False)
        response = pay(self.client)
        self.assertRedirects(response, reverse('booking', args=[self.hotel.hotelid]), fetch_redirect_response=False)
        self.assertFalse(HotelBooking.objects.exists())

    def test_summary_books_the_hotel_in_the_url(self, _weather):
        # Two tabs: both hotel pages are opened, then a suite is picked in the first one.
        self.client.get(reverse('booking', args=[self.hotel.hotelid]))
        self.client.get(reverse('booking', args=[self.other_hotel.hotelid]))
        self.client.get(self.summary_url(self.hotel))
        pay(self.client)
        self.assertEqual(HotelBooking.objects.get().hotel, self.hotel)

    def test_payment_token_must_match_current_booking(self, _weather):
        self.client.get(self.summary_url(self.hotel))
        stale_token = self.client.session['pending_booking']['token']
        self.client.get(self.summary_url(self.other_hotel))
        response = self.client.post(reverse('payment'), {**VALID_CARD, 'token': stale_token})
        self.assertRedirects(response, reverse('payment'))
        self.assertFalse(HotelBooking.objects.exists())

    def test_total_is_recalculated_at_payment(self, _weather):
        self.client.get(self.summary_url(self.hotel))
        Suites.objects.filter(pk=self.suite.pk).update(price_per_night=9000)
        pay(self.client)
        self.assertEqual(HotelBooking.objects.get().payment_price, 3 * (1000 + 9000))

    def test_past_check_in_is_rejected_at_payment(self, _weather):
        self.client.get(self.summary_url(self.hotel))
        session = self.client.session
        session['pending_booking']['check_in'] = (TODAY - timedelta(days=1)).isoformat()
        session.save()
        response = pay(self.client)
        self.assertRedirects(response, reverse('search'))
        self.assertFalse(HotelBooking.objects.exists())

    def test_corrupt_pending_booking_is_cleared(self, _weather):
        session = self.client.session
        session['pending_booking'] = {'type': 'hotel', 'hotel_id': 999, 'token': 'x'}
        session.save()
        response = self.client.get(reverse('payment'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('pending_booking', self.client.session)

    def test_hotel_details_page(self, _weather):
        response = self.client.get(reverse('hotel_details', args=[self.hotel.hotelid]))
        self.assertContains(response, 'Monal')


class SeatConstraintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass12345')
        airline = Airline.objects.create(airline_name='PIA')
        self.flight = Flight.objects.create(
            airline=airline, departure_date=TODAY + timedelta(days=1), departure_time=time(12),
            departure_city='Lahore', destination_city='Karachi', price=10000,
        )

    def test_database_refuses_a_seat_sold_twice(self):
        booking = FlightBooking.objects.create(user=self.user, flight=self.flight, num_seats=1)
        FlightBookedSeats.objects.create(booking=booking, flight=self.flight, seat_no=1)
        with self.assertRaises(IntegrityError):
            FlightBookedSeats.objects.create(booking=booking, flight=self.flight, seat_no=1)

    def test_insert_race_is_reported_as_taken_seat(self):
        self.client.force_login(self.user)
        self.client.post(reverse('plane_seat_selection', args=[self.flight.pk]), {'seats': ['1']})
        # Simulate another payment winning between the availability check and the insert.
        with mock.patch('bookings.views.booked_seats', return_value=set()):
            other = FlightBooking.objects.create(user=self.user, flight=self.flight, num_seats=1)
            FlightBookedSeats.objects.create(booking=other, flight=self.flight, seat_no=1)
            response = pay(self.client)
        self.assertRedirects(response, reverse('plane_seat_selection', args=[self.flight.pk]))
        self.assertEqual(FlightBooking.objects.count(), 1)

    def test_trip_departed_earlier_today_cannot_be_booked(self):
        earlier = timezone.localtime() - timedelta(hours=1)
        if earlier.date() != TODAY:
            self.skipTest("Too close to midnight to have an earlier departure today.")
        self.flight.departure_date, self.flight.departure_time = TODAY, earlier.time()
        self.flight.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('plane_seat_selection', args=[self.flight.pk]))
        self.assertRedirects(response, reverse('search_flights'))

    def test_search_page_lists_airlines(self):
        response = self.client.get(reverse('search_flights') + '?operator=pia')
        self.assertEqual(list(response.context['operators']), ['PIA'])
        self.assertContains(response, '<option value="PIA" selected>')


class AccountTests(TestCase):
    def test_duplicate_phone_number_is_a_form_error(self):
        User_info.objects.create(user=User.objects.create_user('alice', password='pass12345'), phone_no='0300')
        self.client.force_login(User.objects.create_user('bob', password='pass12345'))
        response = self.client.post(reverse('change_profile'), {'phone_no': '0300', 'email': 'b@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('phone_no', response.context['form'].errors)

    def test_profile_saves_and_redirects(self):
        user = User.objects.create_user('alice', password='pass12345')
        self.client.force_login(user)
        response = self.client.post(reverse('change_profile'), {
            'email': 'a@example.com', 'first_name': 'Alice', 'phone_no': '0311', 'city': 'Lahore',
        })
        self.assertRedirects(response, reverse('change_profile'))
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.profile.phone_no, user.profile.city), ('Alice', '0311', 'Lahore'))

    def test_register_creates_profile_and_staff_see_every_user(self):
        self.client.post(reverse('register'), {
            'username': 'newbie', 'password1': 'a-strong-pass-123', 'password2': 'a-strong-pass-123',
        })
        self.assertTrue(User_info.objects.filter(user__username='newbie').exists())
        User.objects.create_user('no-profile', password='pass12345')
        self.client.force_login(User.objects.create_user('admin', password='pass12345', is_staff=True))
        response = self.client.get(reverse('all_users'))
        self.assertEqual(
            sorted(u.username for u in response.context['users']), ['admin', 'newbie', 'no-profile'],
        )

    def test_log_out_requires_post(self):
        self.client.force_login(User.objects.create_user('alice', password='pass12345'))
        self.assertEqual(self.client.get(reverse('log_out')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('log_out')), reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_change_password(self):
        user = User.objects.create_user('alice', password='pass12345')
        self.client.force_login(user)
        response = self.client.post(reverse('change_password'), {
            'old_password': 'pass12345', 'new_password1': 'another-pass-456', 'new_password2': 'another-pass-456',
        })
        self.assertRedirects(response, reverse('change_password'))
        user.refresh_from_db()
        self.assertTrue(user.check_password('another-pass-456'))

    def test_card_expiring_this_month_is_accepted(self):
        from .forms import PaymentForm
        form = PaymentForm({**VALID_CARD, 'expiry': TODAY.strftime('%m/%y')})
        self.assertTrue(form.is_valid(), form.errors)
        form = PaymentForm({**VALID_CARD, 'expiry': (TODAY.replace(day=1) - timedelta(days=1)).strftime('%m/%y')})
        self.assertIn('expiry', form.errors)


class PageTests(TestCase):
    def test_public_pages_render(self):
        for name in ('home', 'aboutus', 'search', 'search_flights', 'search_buses', 'log_in', 'register'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_seed_demo_is_repeatable(self):
        call_command('seed_demo', days=2, stdout=mock.MagicMock())
        call_command('seed_demo', days=2, stdout=mock.MagicMock())
        self.assertEqual(Hotel.objects.filter(name='Monal').count(), 1)
        self.assertTrue(RoomAvailability.objects.filter(date=TODAY + timedelta(days=1)).exists())
