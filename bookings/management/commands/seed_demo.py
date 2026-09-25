from datetime import date, time, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from bookings.models import Airline, Bus, BusCompany, Flight, Hotel, HotelServices, RoomAvailability, Suites

CITIES = ['Lahore', 'Karachi', 'Islamabad']
AIRLINES = {'PIA': 14000, 'AIRSIAL': 12500, 'AIRBLUE': 13000}
BUS_COMPANIES = {'DAEWOO': 3500, 'FAISAL': 2800, 'ROAD MASTER': 3000}
# (name, country, city, price_per_night, services)
HOTELS = [
    ('Monal', 'Pakistan', 'Islamabad', 100, ['Free Wifi', 'Parking', 'Laundry']),
    ('Serena', 'Pakistan', 'Swat', 10000, ['Free Wifi', 'Pool', 'Gym']),
    ('Pearl Continental', 'Pakistan', 'Lahore', 12000, ['Free Wifi', 'Pool', 'Restaurant']),
    ('Nishat Hotel', 'Pakistan', 'Lahore', 9000, ['Free Wifi', 'Spa']),
    ('Ramada', 'Pakistan', 'Karachi', 8000, ['Free Wifi', 'Parking', 'Airport Shuttle']),
    ('Shelton Rezidor', 'Pakistan', 'Swat', 10000, ['Parking', 'Mountain View']),
    ('Hotel One', 'Pakistan', 'Swat', 10000, ['Free Wifi', 'Parking']),
    ('La Crese', 'France', 'Paris', 100, ['Free Wifi', 'Breakfast']),
]
# (name, description, bedrooms, size in sq m, price_per_night)
SUITES = [
    ('Deluxe Suite', 'Our deluxe rooms are cozy, well-appointed and favored by our leisure travellers.', 1, 27, 7000),
    ('Twin Suite', 'Our twin bedrooms are absolutely ethereal with two twin beds', 2, 27, 10000),
    ('Platinum Suite', 'Our platinum suits are generously proportioned for families', 1, 45, 20000),
    ('Presidential Suite', "Presidential suite is a stunning complement to the hotel's elegance and endless style", 3, 90, 50000),
]


class Command(BaseCommand):
    help = "Create demo hotels, suites, flights, buses and hotel availability for the next few weeks. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=14, help="How many days of trips to create (default 14).")

    def handle(self, *args, **options):
        Group.objects.get_or_create(name='customers')
        today = date.today()
        days = [today + timedelta(days=n) for n in range(options['days'])]
        routes = [(a, b) for a in CITIES for b in CITIES if a != b]

        hotels = 0
        for name, country, city, price, services in HOTELS:
            hotel, created = Hotel.objects.get_or_create(
                name=name, defaults={'country': country, 'city': city, 'price_per_night': price},
            )
            hotels += created
            for service in services:
                HotelServices.objects.get_or_create(hotel=hotel, service=service)

        suites = 0
        for name, description, bedrooms, size, price in SUITES:
            _, created = Suites.objects.get_or_create(
                name=name,
                defaults={'description': description, 'bedrooms': bedrooms, 'size': size, 'price_per_night': price},
            )
            suites += created

        flights = 0
        for hour, (name, price) in zip((8, 13, 19), AIRLINES.items()):
            airline, _ = Airline.objects.get_or_create(airline_name=name)
            for day in days:
                for departure, destination in routes:
                    _, created = Flight.objects.get_or_create(
                        airline=airline, departure_date=day, departure_time=time(hour),
                        departure_city=departure, destination_city=destination,
                        defaults={'price': price},
                    )
                    flights += created

        buses = 0
        for hour, (name, price) in zip((7, 12, 22), BUS_COMPANIES.items()):
            company, _ = BusCompany.objects.get_or_create(company_name=name)
            for day in days:
                for departure, destination in routes:
                    _, created = Bus.objects.get_or_create(
                        company=company, departure_date=day, departure_time=time(hour),
                        departure_city=departure, destination_city=destination,
                        defaults={'price': price},
                    )
                    buses += created

        availability = 0
        for hotel in Hotel.objects.all():
            for n in range(30):
                _, created = RoomAvailability.objects.get_or_create(name=hotel, date=today + timedelta(days=n))
                availability += created

        self.stdout.write(self.style.SUCCESS(
            f"Created {hotels} hotels, {suites} suites, {flights} flights, {buses} buses and {availability} hotel availability days."
        ))
