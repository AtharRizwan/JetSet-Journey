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
        return self.first_name
    

class Hotel(models.Model):
    hotelid = models.AutoField(primary_key=True)
    name = models.CharField(max_length = 250, unique= True)    
    country = models.CharField(max_length = 250)    
    city = models.CharField(max_length = 250)    

    def __str__(self):
        return self.name 

class RoomAvailability(models.Model):
    name = models.ForeignKey(Hotel, on_delete=models.CASCADE, to_field='name')
    date = models.DateField()
    isAvailable = models.BooleanField(default=True)

    def __str__(self):
        return self.date
    