from django.db import models
from django.contrib.auth.models import User # Import built in User model
# Create your models here.

class User_info(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) #Craetes one to one relationship
    phone_no = models.CharField(max_length=50, unique=True)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
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

class RoomAvailability(models.Model):
    name = models.ForeignKey(Hotel, on_delete=models.CASCADE, to_field='name')
    date = models.DateField()
    isAvailable = models.BooleanField(default=True)

    def __str__(self):
        return self.date

class CreditCard(models.Model):
    card_no = models.CharField(max_length=50, primary_key=True)
    bank_name = models.CharField(max_length=50,default = "")
    cvc = models.IntegerField()
    expiry_date = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
class HotelBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    no_of_days = models.IntegerField(default = 0)
    payment_price = models.IntegerField(default = 0)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.IntegerField()
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    room_choices = [
        ('Standard', 'Standard'),
        ('Deluxe', 'Deluxe'),
        ('Suite', 'Suite'),
    ]
    room_preference = models.CharField(max_length=20, 
                                       choices=room_choices, null = True, blank = True)
    special_requests = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.room_preference} Room"



