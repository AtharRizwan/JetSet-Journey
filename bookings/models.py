from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class User_info(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    city = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.user.username


class Hotel(models.Model):
    hotelid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250, unique=True)
    country = models.CharField(max_length=250)
    city = models.CharField(max_length=250)
    price_per_night = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.name


class HotelServices(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, to_field='hotelid')
    service = models.CharField(max_length=50)

    def __str__(self):
        return self.service


class Suites(models.Model):
    suiteid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=250)
    bedrooms = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    size = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])
    price_per_night = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.name


class RoomAvailability(models.Model):
    """One row per hotel per open/closed date; a night with no row is not bookable."""
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    date = models.DateField()
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['hotel', 'date'], name='unique_hotel_availability_date'),
        ]

    def __str__(self):
        return f"{self.hotel} {self.date} ({'open' if self.is_available else 'closed'})"


class HotelBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hotel = models.ForeignKey(Hotel, on_delete=models.PROTECT)
    suite = models.ForeignKey(Suites, on_delete=models.PROTECT, to_field='suiteid')
    check_in = models.DateField()
    check_out = models.DateField()
    no_of_days = models.PositiveIntegerField(default=1)
    payment_price = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(check_out__gt=F('check_in')), name='hotel_booking_check_out_after_check_in'),
        ]

    def __str__(self):
        return f"{self.hotel} - {self.suite}"


class Airline(models.Model):
    airline_id = models.AutoField(primary_key=True)
    airline_name = models.CharField(max_length=50)

    def __str__(self):
        return self.airline_name


class Flight(models.Model):
    flightid = models.AutoField(primary_key=True)
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE, to_field='airline_id')
    departure_date = models.DateField()
    departure_time = models.TimeField(default="12:00:00")
    departure_city = models.CharField(max_length=250)
    destination_city = models.CharField(max_length=250)
    price = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.departure_city + " to " + self.destination_city


class FlightBooking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT)
    num_seats = models.PositiveIntegerField(default=1)
    payment_price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.flight}"


class FlightBookedSeats(models.Model):
    booking = models.ForeignKey(FlightBooking, on_delete=models.CASCADE)
    # Duplicates booking.flight so the database can refuse a seat being sold twice.
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT)
    seat_no = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['flight', 'seat_no'], name='unique_flight_seat'),
        ]

    def __str__(self):
        return str(self.seat_no)


class BusCompany(models.Model):
    company_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=50)

    def __str__(self):
        return self.company_name


class Bus(models.Model):
    busid = models.AutoField(primary_key=True)
    company = models.ForeignKey(BusCompany, on_delete=models.CASCADE, to_field='company_id')
    departure_date = models.DateField()
    departure_time = models.TimeField(default="12:00:00")
    departure_city = models.CharField(max_length=250)
    destination_city = models.CharField(max_length=250)
    price = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.departure_city + " to " + self.destination_city


class BusBooking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT)
    num_seats = models.PositiveIntegerField(default=1)
    payment_price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.bus}"


class BusBookedSeats(models.Model):
    booking = models.ForeignKey(BusBooking, on_delete=models.CASCADE)
    # Duplicates booking.bus so the database can refuse a seat being sold twice.
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT)
    seat_no = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['bus', 'seat_no'], name='unique_bus_seat'),
        ]

    def __str__(self):
        return str(self.seat_no)
