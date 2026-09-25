from django.contrib import admin

from .models import (
    Airline, Bus, BusBookedSeats, BusBooking, BusCompany, Flight, FlightBookedSeats, FlightBooking,
    Hotel, HotelBooking, HotelServices, RoomAvailability, Suites, User_info,
)

for model in (
    Hotel, RoomAvailability, User_info, Suites, HotelServices, HotelBooking,
    Airline, Flight, FlightBooking, FlightBookedSeats,
    BusCompany, Bus, BusBooking, BusBookedSeats,
):
    admin.site.register(model)
