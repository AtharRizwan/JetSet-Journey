from django.contrib import admin

# Register your models here.
from .models import Hotel, RoomAvailability, User_info, Airline, Flight, FlightBooking, FlightBookedSeats, Suites, HotelServices, CreditCard

admin.site.register(Hotel)
admin.site.register(RoomAvailability)
admin.site.register(User_info)
admin.site.register(Airline)
admin.site.register(Flight)
admin.site.register(FlightBooking)
admin.site.register(FlightBookedSeats)
admin.site.register(Suites)
admin.site.register(HotelServices)
admin.site.register(CreditCard)