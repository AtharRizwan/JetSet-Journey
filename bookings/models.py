from django.db import models
from django.contrib.auth.models import User # Import built in User model
# Create your models here.

class User_info(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) #Craetes one to one relationship
    phone_no = models.CharField(max_length=50, unique=True, null=True, blank=True)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100, default="")
    last_name = models.CharField(max_length=100, default="")
    state = models.CharField(max_length=50, default="")
    zip_code = models.IntegerField(default=10000)
    email = models.EmailField(default="")
    def __str__(self):
        return self.user.first_name 
    
class Hotel(models.Model):
    hotelid = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 250, unique= True)    
    country = models.CharField(max_length = 250)    
    city = models.CharField(max_length = 250)    
    price_per_night = models.IntegerField(default=100)
    def __str__(self):
        return self.name 
    
class HotelServices(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, to_field='hotelid')
    service = models.CharField(max_length=50)
    def __str__(self):
        return self.service
    
class Suites(models.Model):
    suiteid = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 250)
    description = models.CharField(max_length = 250)
    bedrooms = models.IntegerField(default=100)
    size = models.IntegerField(default=100)    
    price_per_night = models.IntegerField(default=100)
    def __str__(self):
        return self.name    

class RoomAvailability(models.Model):
    name = models.ForeignKey(Hotel, on_delete=models.CASCADE, to_field='name')
    date = models.DateField()
    isAvailable = models.BooleanField(default=True)

class HotelBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    no_of_days = models.IntegerField(default = 0)
    payment_price = models.IntegerField(default = 0)
    suite_id = models.ForeignKey(Suites, on_delete=models.CASCADE, to_field='suiteid', default=1)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.hotel} - {self.suite_id}"

class Airline(models.Model):
    airline_id = models.AutoField(primary_key=True)
    airline_name = models.CharField(max_length=50)
    def __str__(self):
        return self.airline_name
    
class Flight(models.Model):
    flightid = models.AutoField(primary_key=True)
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE, to_field='airline_id')
    departure_date = models.DateField(default = "2023-12-30")
    departure_time = models.TimeField(default = "12:00:00")
    departure_city = models.CharField(max_length = 250)    
    destination_city = models.CharField(max_length = 250)    
    price = models.IntegerField(default=100)
    def __str__(self):
        return self.departure_city + " to " + self.destination_city

class FlightBooking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    num_seats = models.IntegerField(default = 0)
    payment_price = models.IntegerField(default = 0)
    def __str__(self):
        return f"{self.user.username} - {self.flight}"
    
class FlightBookedSeats(models.Model):
    booking_id = models.ForeignKey(FlightBooking, on_delete=models.CASCADE)
    seat_no = models.IntegerField()
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
    departure_date = models.DateField(default = "2023-12-30")
    departure_time = models.TimeField(default = "12:00:00")
    departure_city = models.CharField(max_length = 250)    
    destination_city = models.CharField(max_length = 250)    
    price = models.IntegerField(default=100)
    def __str__(self):
        return self.departure_city + " to " + self.destination_city
    
class BusBooking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    num_seats = models.IntegerField(default = 0)
    payment_price = models.IntegerField(default = 0)
    def __str__(self):
        return f"{self.user.username} - {self.bus}"
    
class BusBookedSeats(models.Model):
    booking_id = models.ForeignKey(BusBooking, on_delete=models.CASCADE)
    seat_no = models.IntegerField()
    def __str__(self):
        return str(self.seat_no)
