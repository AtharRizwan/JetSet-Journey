from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name = "home"),
    path('register', views.register, name = "register"),
    path('log_in', views.log_in, name = "log_in"),
    path('log_out', views.log_out, name = "log_out"),
    path('all_users', views.all_users, name = "all_users"),
    path('change_profile', views.change_profile, name = "change_profile"),
    path('change_password/', views.change_password, name='change_password'),
    path('add_hotel/', views.add_hotel, name='add_hotel'),
    path('search/', views.search, name = "search"),
    path('searched_hotels', views.searched_hotels, name='searched_hotels'),
    path('searched_hotels/<int:id>', views.hotel_details, name='hotel_details'),
    path('booking/<int:id>', views.booking, name='booking'),
    path('hotel_summary/<int:id>', views.hotel_summary, name='hotel_summary'),
    path('all_bookings', views.all_bookings, name = "all_bookings"),
    path('payment/', views.payment, name='payment'),
    path('search_flights/', views.search_flights, name='search_flights'),
    path('flights_informations/', views.flights_informations, name='flights_informations'),
    path('flights_informations/<int:id>', views.flight_details, name='flights_information'),
    path('plane_seat_selection/<int:id>', views.plane_seat_selection, name='plane_seat_selection'),
    path('search_buses/', views.search_buses, name='search_buses'),
    path('buses_informations/', views.buses_informations, name='buses_informations'),
    path('buses_informations/<int:id>', views.bus_details, name='buses_information'),
    path('bus_seat_selection/<int:id>', views.bus_seat_selection, name='bus_seat_selection')
]
