from datetime import time, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Airline, Bus, BusCompany, Flight, Hotel, HotelServices, RoomAvailability, Suites

FLIGHT_CITIES = ['Lahore', 'Karachi', 'Islamabad', 'Paris']
BUS_CITIES = ['Lahore', 'Karachi', 'Islamabad', 'Swat']
AIRLINES = {'PIA': 14000, 'AIRSIAL': 12500, 'AIRBLUE': 13000}
BUS_COMPANIES = {'DAEWOO': 3500, 'FAISAL': 2800, 'ROAD MASTER': 3000}
# (name, country, city, price_per_night, services)
HOTELS = [
    ('Monal', 'Pakistan', 'Islamabad', 6000, ['Free Wifi', 'Parking', 'Laundry']),
    ('Serena', 'Pakistan', 'Swat', 10000, ['Free Wifi', 'Pool', 'Gym']),
    ('Pearl Continental', 'Pakistan', 'Lahore', 12000, ['Free Wifi', 'Pool', 'Restaurant']),
    ('Nishat Hotel', 'Pakistan', 'Lahore', 9000, ['Free Wifi', 'Spa']),
    ('Ramada', 'Pakistan', 'Karachi', 8000, ['Free Wifi', 'Parking', 'Airport Shuttle']),
    ('Shelton Rezidor', 'Pakistan', 'Swat', 10000, ['Parking', 'Mountain View']),
    ('Hotel One', 'Pakistan', 'Swat', 10000, ['Free Wifi', 'Parking']),
    ('La Crese', 'France', 'Paris', 20000, ['Free Wifi', 'Breakfast']),
    # The home page's popular destinations.
    ('Hudson Grand', 'USA', 'New York', 25000, ['Free Wifi', 'Gym', 'Restaurant']),
    ('Thames View Hotel', 'UK', 'London', 22000, ['Free Wifi', 'Breakfast']),
    ('Canal House', 'Netherlands', 'Amsterdam', 18000, ['Free Wifi', 'Bicycle Rental']),
    ('Harbour Lights', 'Australia', 'Sydney', 21000, ['Free Wifi', 'Pool', 'Harbour View']),
    ('Sakura Inn', 'Japan', 'Kyoto', 16000, ['Free Wifi', 'Garden', 'Breakfast']),
]
# (name, description, bedrooms, size in sq m, price_per_night)
SUITES = [
    ('Deluxe Suite', 'Our deluxe rooms are cozy, well-appointed and favored by our leisure travellers.', 1, 27, 7000),
    ('Twin Suite', 'Our twin bedrooms are absolutely ethereal with two twin beds', 2, 27, 10000),
    ('Platinum Suite', 'Our platinum suits are generously proportioned for families', 1, 45, 20000),
    ('Presidential Suite', "Presidential suite is a stunning complement to the hotel's elegance and endless style", 3, 90, 50000),
]


class Command(BaseCommand):
    help = "Create or update demo hotels, suites, flights, buses and hotel availability for the coming days. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help="How many days of trips and hotel availability to create (default 30).")

    def handle(self, *args, **options):
        Group.objects.get_or_create(name='customers')
        today = timezone.localdate()
        days = [today + timedelta(days=n) for n in range(options['days'])]

        hotels = 0
        for name, country, city, price, services in HOTELS:
            hotel, created = Hotel.objects.update_or_create(
                name=name, defaults={'country': country, 'city': city, 'price_per_night': price},
            )
            hotels += created
            for service in services:
                HotelServices.objects.get_or_create(hotel=hotel, service=service)

        suites = 0
        for name, description, bedrooms, size, price in SUITES:
            _, created = Suites.objects.update_or_create(
                name=name,
                defaults={'description': description, 'bedrooms': bedrooms, 'size': size, 'price_per_night': price},
            )
            suites += created

        flights = 0
        routes = [(a, b) for a in FLIGHT_CITIES for b in FLIGHT_CITIES if a != b]
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
        routes = [(a, b) for a in BUS_CITIES for b in BUS_CITIES if a != b]
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
            for day in days:
                _, created = RoomAvailability.objects.get_or_create(hotel=hotel, date=day)
                availability += created

        self.stdout.write(self.style.SUCCESS(
            f"Created {hotels} hotels, {suites} suites, {flights} flights, {buses} buses and {availability} hotel availability days."
        ))
