from django.contrib import admin

# Register your models here.
from .models import Hotel, RoomAvailability, User_info

admin.site.register(Hotel)
admin.site.register(RoomAvailability)
admin.site.register(User_info)