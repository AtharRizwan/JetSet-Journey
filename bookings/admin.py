from django.contrib import admin

from .models import (
    Airline, Bus, BusBookedSeats, BusBooking, BusCompany, Flight, FlightBookedSeats, FlightBooking,
    Hotel, HotelBooking, HotelServices, RoomAvailability, Suites, User_info,
)

admin.site.register(Airline)
admin.site.register(BusCompany)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'price_per_night')
    search_fields = ('name', 'city')


@admin.register(HotelServices)
class HotelServicesAdmin(admin.ModelAdmin):
    list_display = ('service', 'hotel')
    list_select_related = ('hotel',)


@admin.register(Suites)
class SuitesAdmin(admin.ModelAdmin):
    list_display = ('name', 'bedrooms', 'size', 'price_per_night')


@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'date', 'is_available')
    list_filter = ('is_available', 'hotel')
    list_select_related = ('hotel',)


@admin.register(User_info)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_no', 'city', 'country')
    list_select_related = ('user',)


@admin.register(HotelBooking)
class HotelBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'hotel', 'suite', 'check_in', 'check_out', 'payment_price')
    list_select_related = ('user', 'hotel', 'suite')


@admin.register(Flight, Bus)
class TripAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'departure_date', 'departure_time', 'price')
    list_filter = ('departure_date',)


@admin.register(FlightBooking)
class FlightBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'flight', 'num_seats', 'payment_price')
    list_select_related = ('user', 'flight')


@admin.register(BusBooking)
class BusBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'num_seats', 'payment_price')
    list_select_related = ('user', 'bus')


@admin.register(FlightBookedSeats)
class FlightBookedSeatsAdmin(admin.ModelAdmin):
    list_display = ('seat_no', 'flight', 'booking')
    list_select_related = ('flight', 'booking__user', 'booking__flight')


@admin.register(BusBookedSeats)
class BusBookedSeatsAdmin(admin.ModelAdmin):
    list_display = ('seat_no', 'bus', 'booking')
    list_select_related = ('bus', 'booking__user', 'booking__bus')
